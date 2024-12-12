#!/bin/bash

set -e          # error and quit when( $? != 0 )
set -u          # error and quit on unbound variable
set -o pipefail # halt when a pipe failure occurs
#set -x          # execute and print

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

declare -A stats=(
    ["fetch"]="$(if [ "${fetch:-0}" = "1" ]; then echo "Fail"; else echo "-"; fi)"
    ["prepare"]="$(if [ "${prepare:-0}" = "1" ]; then echo "Fail"; else echo "-"; fi)"
    ["build"]="$(if [ "${build:-0}" = "1" ]; then echo "Fail"; else echo "-"; fi)"
    ["test"]="$(if [ "${test:-0}" = "1" ]; then echo "Fail"; else echo "-"; fi)"
)

function PrintStats {
    for key in "${!stats[@]}"; do
        echo "stats[\"$key\"]=\"${stats[$key]}\""
    done
}

trap "PrintStats; exit 1" 0

# Check needed vars
if [ -z "${root:-}" ]; then exit 1; fi
if [ -z "${script:-}" ]; then exit 1; fi

source "$root/share/format.sh"

# Get the target root from this script location
targetRoot=${targetRoot:-$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )}
cd "$targetRoot" || return 1

# determine the config from the script name.
config="${config:-${script%.*}}"

buildRoot="$targetRoot/$config"

#gitUrl=http://github.com/enetheru/godot-cpp.git
gitUrl=${gitUrl:-"http://github.com/enetheru/godot-cpp.git"}
gitBranch=${gitBranch:-"master"}

godot="/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
godot_tr="/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"

H2 " Build ${target:-FailTarget} using ${platform:-FailPlatform} "
echo "
  script      = ${script:-}
  Build Root  = ${buildRoot:-}

  fetch       = ${fetch:-}
  prepare     = ${prepare:-}
  build       = ${build:-}
  test        = ${test:-}
  jobs        = ${jobs:-}

  fresh build = ${fresh:-}
  log append  = ${append:-}

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch

  godot       = $godot
  godot_tr    = $godot_tr"

# Host Platform Values and Functions
source "$root/share/build-actions.sh"

# Some # Project overrides and functions are identical.
PrepareCommon(){
    local prev
    prev="$(pwd)"

    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    fragments=".*(memory|libgodot-cpp|libgdexample).*"
    extensions="(o|os|a|lib|so|dll|dylib)"
    mapfile -t artifacts < <(
        find . -type f -regex "$fragments\.$extensions" -print
        )

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

# override build actions
source "$targetRoot/$script"

H3 "$config - Processing"

if [ "$fetch" -eq 1 ]; then
    if ! Fetch;     then Error "Fetch Failure"  ; exit 1; fi
    stats["fetch"]="OK"
fi

if [ "$prepare" -eq 1 ]; then
    if ! Prepare;   then Error "Prepare Failure"; exit 1; fi
    stats["prepare"]="OK"
fi

if [ "$build" -eq 1 ]; then
    if ! Build;     then Error "Build Failure"  ; exit 1; fi
    stats["build"]="OK"
fi

if [ "$test" -eq 1 ]; then
#    if ! Test 5>&1; then Error "Test Failure"   ; fi
    Test
    stats["test"]="OK"
fi

H2 "$config - completed"

PrintStats
