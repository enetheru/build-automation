#!/bin/zsh


# Configuration variables and functions to pass the main script
# Note, the main script is bash, so this needs to conform to bash standards.
if [ "$1" = "get_config" ]; then
    gitUrl=${gitUrl:-"http://github.com/enetheru/godot-cpp.git"}
    gitBranch=${gitBranch:-"master"}

    function CleanLog {
        H3 "TODO CleanLog for godot-cpp/Darwin-actions.sh"
    }
    return
fi

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

cd "$targetRoot" || return 1


declare -i columns=120
source "$root/share/format.sh"

H2 " Build $target using $platform "
echo "
  script      = $script
  fetch       = $fetch
  configure   = $configure
  build       = $build
  test        = $test

  fresh build = $fresh
  log append  = $append"

#gitUrl=http://github.com/enetheru/godot-cpp.git
gitUrl=${gitUrl:-"http://github.com/enetheru/godot-cpp.git"}
gitBranch=${gitBranch:-"master"}

echo "
  gitUrl      = $gitUrl
  gitBranch   = $gitBranch"

godot="/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
godot_tr="/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"

echo "
  godot       = $godot
  godot_tr    = $godot_tr"

# Get the target root from this script location
targetRoot=${targetRoot:-$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )}

# Some steps are identical.
PrepareCommon(){
    local prev
    prev="$(pwd)"

    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    fragments=".*(memory|libgodot-cpp|libgdexample).*"
    extensions="(o|os|a|lib|so|dll|dylib)"
    artifacts=($(find -E . -type f -regex "$fragments\.$extensions" -print ))

    if [ ${#artifacts} -gt 0 ]; then
        Warning "Deleting ${#artifacts} Artifacts"
        printf "%s\n" "${artifacts[@]}" | tee >(cat >&5) | xargs rm
    fi

    # zsh will error if there is a glob failure.
    setopt NULL_GLOB
    genDirs=(cmake-build-*/gen)
    unsetopt NULL_GLOB
    if [ ${#genDirs} -gt 0 ]; then
        Warning "Deleting generated files"
        printf "%s\n" "${genDirs[@]}" | tee >(cat >&5) | xargs rm -r
    fi

    cd "$prev"
}

TestCommon(){
    local result

    H1 "Test"

    printf "\n" >> "$targetRoot/summary.log"
    H4 "$config" >> "$targetRoot/summary.log"

    if [ ! -d "$buildRoot/test/project/.godot" ]; then
        H4 "Generate the .godot folder"
        Format-Command "$godot -e --path \"$buildRoot/test/project/\" --quit --headless"

        # Capture the output of this one silently because it always fails, and
        # succeeds. We can dump it if it's a real failure.
        result=$($godot -e --path "$buildRoot/test/project/" --quit --headless 2>&1)

        if [ ! -d "$buildRoot/test/project/.godot" ]; then
            echo "$result"
            Error "Creating .godot folder" >> "$targetRoot/summary.log"
            return 1
        fi
    else
        H4 "The .godot folder has already been generated."
    fi

    H4 "Run the test project"
    Format-Command "$godot_tr --path \"$buildRoot/test/project/\" --quit --headless"

    # Because of the capture of stdout for the variable, we need to tee it to a
    # custom file descriptor which is being piped to stdout elsewhere.
    result="$($godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
        | tee >(cat >&5))"

    # Split the result into lines, skip the empty ones.
    declare -a lines=()
    while IFS=$'\n' read -ra line; do
        if [ -n "${line//[[:space:]]/}" ]; then
            lines+=("$line") 
        fi
    done <<< "$result"

    printf "%s\n" "${lines[@]}" >> "$targetRoot/summary.log"

    # returns true if the last line includes PASSED
    [[ "${lines[-1]}" == *"PASSED"* ]]
}



config="${script%.*}"
buildRoot="$targetRoot/$config"

# generic build actions.
source "$root/share/build-actions.sh"

# override build actions
source "$targetRoot/$script"

H2 "Processing - $config"
echo "  Build Root = $buildRoot"

if [ "$fetch" -eq 1 ]; then
  if ! Fetch;     then Error "Fetch Failure"  ; exit 1; fi
fi

if [ "$configure" -eq 1 ]; then
  if ! Prepare;   then Error "Prepare Failure"; exit 1; fi
fi

if [ "$build" -eq 1 ]; then
  if ! Build;     then Error "Build Failure"  ; exit 1; fi
fi

if [ "$test" -eq 1 ]; then
  if ! Test 5>&1; then Error "Test Failure"   ; fi
fi

if ! Clean;     then Error "Clean Failure"  ; fi

H3 "Completed - $config"

