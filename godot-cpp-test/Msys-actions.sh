#!/bin/bash

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

declare -i columns=120
source "$root/share/format.sh"

# Get the target root from this script location
targetRoot=${targetRoot:-$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )}

cd "$targetRoot" || return 1

config="${script%.*}"
buildRoot="$targetRoot/$config"

# generic build actions.
source "$root/share/build-actions.sh"

# override build actions
source "$targetRoot/$script"

H2 " Build $target using $platform "
echo "
  script      = $script
  Build Root  = $buildRoot
  fetch       = $fetch
  configure   = $configure
  build       = $build
  test        = $test

  fresh build = $fresh
  log append  = $append"

#gitUrl=http://github.com/enetheru/godot-cpp.git
gitUrl=${gitUrl:-"http://github.com/enetheru/godot-cpp-test.git"}
gitBranch=${gitBranch:-"main"}

echo "
  gitUrl      = $gitUrl
  gitBranch   = $gitBranch"

godot="/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
godot_tr="/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"

echo "
  godot       = $godot
  godot_tr    = $godot_tr"


# Some steps are identical.
PrepareCommon(){
    local prev
    prev="$(pwd)"

    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    fragments=".*(memory|libgodot-cpp|libgdexample).*"
    extensions="(o|os|a|lib|so|dll|dylib)"
    artifacts=($(find . -type f -regex "$fragments\.$extensions" -print ))

    if [ ${#artifacts} -gt 0 ]; then
        Warning "Deleting ${#artifacts} Artifacts"
        printf "%s\n" "${artifacts[@]}" | tee >(cat >&5) | xargs rm
    fi

    # bash null glob failure
    shopt -s nullglob
    genDirs=(cmake-build-*/gen)
    shopt -u nullglob
    if [ ${#genDirs} -gt 0 ]; then
        Warning "Deleting generated files"
        printf "%s\n" "${genDirs[@]}" | tee >(cat >&5) | xargs rm -r
    fi

    #FIXME what if we are a scons build?

    cd "$prev"
}

TestCommon(){
    local result

    H1 "Test"

    projectDir="$buildRoot/project"

    printf "\n" >> "$targetRoot/summary.log"
    H4 "$config" >> "$targetRoot/summary.log"

    if [ ! -d "$projectDir/.godot" ]; then
        H4 "Generate the .godot folder"

        Format-Eval "$godot -e --path '$projectDir/' --quit --headless" 2>&1

        # Capture the output of this one silently because it always fails, and
        # succeeds. We can dump it if it's a real failure.
        # result=$($godot -e --path "$projectDir" --quit --headless 2>&1)

        if [ ! -d "$projectDir/.godot" ]; then
            echo "$result"
            Error "Creating .godot folder" >> "$targetRoot/summary.log"
            return 1
        fi
    else
        H4 "The .godot folder has already been generated."
    fi

    H4 "Run the test project"
    Format-Command "$godot_tr --path '$projectDir' --quit --headless"

    # Because of the capture of stdout for the variable, we need to tee it to a
    # custom file descriptor which is being piped to stdout elsewhere.
    result="$($godot_tr --path "$projectDir" --quit --headless 2>&1 \
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

H2 "Processing - $config"

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

