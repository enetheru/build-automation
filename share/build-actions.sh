#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

. "$root/share/aarray.sh"

##################################- Utilities -#################################
#                                                                            #
#        ██    ██ ████████ ██ ██      ██ ████████ ██ ███████ ███████         #
#        ██    ██    ██    ██ ██      ██    ██    ██ ██      ██              #
#        ██    ██    ██    ██ ██      ██    ██    ██ █████   ███████         #
#        ██    ██    ██    ██ ██      ██    ██    ██ ██           ██         #
#         ██████     ██    ██ ███████ ██    ██    ██ ███████ ███████         #
#                                                                            #
################################################################################

function EraseFiles {
    cd "$buildRoot" || exit 1

    # Make a list of files to remove based on the below criteria
    fragments="${1:-"NothingToErase"}"
    extensions="${2:-"NoFileExtensionsSpecified"}"

    declare -a artifacts=()
    while IFS= read -r line; do
        artifacts+=("$line")
    done < <(find . -type f -regextype egrep -regex ".*($fragments).*($extensions)$")

    if [ ${#artifacts[0]} -gt 0 ]; then
        H3 "Erase Files"
        Warning "Deleting ${#artifacts[@]} Artifacts"
        for artifact in "${artifacts[@]}"; do
            echo "  Removing '$artifact'"
            rm "$artifact"
        done
    fi
}

# https://mharrison.org/post/bashfunctionoverride/
# Usage: RenameFunction <old-name> <newname>
function RenameFunction {
    local ORIG_FUNC
    ORIG_FUNC=$(declare -f "$1")
    local NEWNAME_FUNC="$2${ORIG_FUNC#"$1"}"
    eval "$NEWNAME_FUNC"
}

function SummariseConfig {
    H2 "Build ${target:-FailTarget} using ${config}"
    echo "
  script      = ${script:-}

  fetch       = ${fetch:-}
  prepare     = ${prepare:-}
  build       = ${build:-}
  test        = ${test:-}

  jobs        = ${jobs:-}
  fresh build = ${fresh:-}
  log append  = ${append:-}

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot"
}

##################################- updates -###################################
#                                                                            #
#         ██    ██ ██████  ██████   █████  ████████ ███████ ███████          #
#         ██    ██ ██   ██ ██   ██ ██   ██    ██    ██      ██               #
#         ██    ██ ██   ██ ██████  ███████    ██    █████   ███████          #
#         ██    ██ ██   ██ ██      ██   ██    ██    ██           ██          #
#          ██████  ██████  ██      ██   ██    ██    ███████ ███████          #
#                                                                            #
################################################################################

# Update Android
function UpdateAndroid {
    H3 "Update Android SDK"

    unset doVerbose
    if [ "${verbose:-1}" -eq 1 ]; then doVerbose="verbose=yes"; fi

    cmdlineTools="/c/androidsdk/cmdline-tools/latest/bin"

    PATH="$cmdlineTools;$PATH"

    Format-Eval "sdkmanager --update $doVerbose"
}

function UpdateEmscripten {
    H3 "Update Emscripten SDK"

    emsdk="/c/emsdk"

    cd $emsdk || exit 1
    Format-Eval "git pull"
    Format-Eval "$emsdk/emsdk install latest"
}

####################################- Fetch -###################################
#                                                                            #
#                  ███████ ███████ ████████  ██████ ██   ██                  #
#                  ██      ██         ██    ██      ██   ██                  #
#                  █████   █████      ██    ██      ███████                  #
#                  ██      ██         ██    ██      ██   ██                  #
#                  ██      ███████    ██     ██████ ██   ██                  #
#                                                                            #
################################################################################

function Fetch {
    set +e
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    Figlet "Git Fetch"

    H3 "Update WorkTree"
    # Checkout worktree if not already
    if [ ! -d "$buildRoot" ]; then
        Format-Eval "git --git-dir=\"$targetRoot/git\" worktree add -d \"$buildRoot\"" || return 1
    fi

    # Update worktree
    cd "$buildRoot" || return 1
    Format-Eval "git checkout --force --detach $gitBranch" || return 1
    Format-Eval "git status" || return 1
    Fill "-"
    set -e
}

##################################- Prepare -###################################
#                                                                            #
#          ██████  ██████  ███████ ██████   █████  ██████  ███████           #
#          ██   ██ ██   ██ ██      ██   ██ ██   ██ ██   ██ ██                #
#          ██████  ██████  █████   ██████  ███████ ██████  █████             #
#          ██      ██   ██ ██      ██      ██   ██ ██   ██ ██                #
#          ██      ██   ██ ███████ ██      ██   ██ ██   ██ ███████           #
#                                                                            #
################################################################################

function Prepare {
    H3 "No Prepare Action Specified"
    echo "-"
}

####################################- Build -###################################
#                                                                            #
#                    ██████  ██    ██ ██ ██      ██████                      #
#                    ██   ██ ██    ██ ██ ██      ██   ██                     #
#                    ██████  ██    ██ ██ ██      ██   ██                     #
#                    ██   ██ ██    ██ ██ ██      ██   ██                     #
#                    ██████   ██████  ██ ███████ ██████                      #
#                                                                            #
################################################################################

function Build {
    H3 "No Build Action Specified"
    echo "-"
}

## Build with SCons
# Function takes two arguments, array of targets, and array of options.
# if both unset, then default build options are used.
function BuildSCons {
    # If no arrayName was supplied then create an empty one
    if [ -z "${1:-}" ];then
        declare -a sconsVars=()
    # Else Reference an existing array if the names dont clash
    elif [ "$1" != "sconsVars" ]; then
        declare -n sconsVars="$1"
    fi

    # If no arrayName was supplied then create an empty one
    if [ -z "${2:-}" ];then
        declare -a targets=("")
    # Else Reference an existing array if the names dont clash
    elif [ "$2" != "targets" ]; then
        declare -n targets="$2"
    fi

    # requires SConstruct file existing in the current directory.
    if [ ! -f "SConstruct" ]; then
        Error "Missing '$(pwd)/SConstruct'"
        return 1
    fi

    unset doJobs
    if [ "${jobs}" -gt 0 ]; then doJobs="-j $jobs"; fi

    unset doVerbose
    if [ "${verbose:-1}" -eq 1 ]; then doVerbose="verbose=yes"; fi

    declare -a buildVars=( "${doJobs:-}" "${doVerbose:-}" )
    if [ ${#sconsVars[@]} -gt 0 ]; then
        buildVars+=("${sconsVars[@]}")
    fi

    for target in "${targets[@]}"; do
        if [ -n "$target" ]; then
            addTarget="target=$target"
        else
            target="default"
        fi

        Figlet "SCons Build" "small"
        H3 "Config: $config"
        H3 "Target: $target"
        start=$SECONDS

        Format-Eval "scons ${buildVars[*]} ${addTarget:-}"

        duration=$(Format-Seconds "$((SECONDS - start))")

        statArray+=( "scons.$target ${duration}")

        H3 "BuildScons Completed"
        printf "%s\n%s" "${statArray[0]}" "${statArray[-1]}" | column -t
        Fill "-"
    done
}

function BuildCMake {
    # requires CMakeCache.txt file existing in the current directory.
    if [ ! -f "CMakeCache.txt" ]; then
        Error "Missing $(pwd)/CMakeCache.txt, Requires configuration."
        return 1
    fi

    # Build Targets using CMake
    unset doVerbose
    if [ "${verbose:-1}" -eq 1 ]; then doVerbose="--verbose"; fi

    unset doJobs
    if [ "${jobs}" -gt 0 ]; then doJobs="-j $jobs"; fi

    if [ -z "${targets:-}" ]; then
        targets=("template_release" "template_debug" "editor")
    fi

    declare -a buildVars=( "${doJobs:-}" "${doVerbose:-}" )
    if [ -n "${cmakeVars:-}" ]; then
        buildVars+=("${cmakeVars[@]}")
    fi

    for target in "${targets[@]}"; do
        Figlet "CMake Build" "small"
        H3 "Config: $config"
        H3 "Target: $target"

        declare -i start=$SECONDS
        Format-Eval "cmake --build . ${cmakeVars[*]} -t godot-cpp.test.$target"
        declare -i seconds=$((SECONDS - start))

        artifact="$buildRoot/test/project/bin/libgdexample.windows.$target.x86_64.dll"
        bytes="$(stat --printf "%s" "$artifact")"
        size=$(Format-Bytes "$bytes")

        duration=$(Format-Seconds "$seconds")

        statArray+=( "cmake.$target ${duration} ${size}")

        H3 "BuildCMake Completed"
        printf "%s\n%s" "${statArray[0]}" "${statArray[-1]}" | column -t
        Fill "-"
    done
}

####################################- Test -####################################
#                                                                            #
#                     ████████ ███████ ███████ ████████                      #
#                        ██    ██      ██         ██                         #
#                        ██    █████   ███████    ██                         #
#                        ██    ██           ██    ██                         #
#                        ██    ███████ ███████    ██                         #
#                                                                            #
################################################################################

function Test {
    H3 "No Test Action Specified"
    echo "-"
}
##################################- Process -###################################
#                                                                              #
#           ██████  ██████   ██████   ██████ ███████ ███████ ███████           #
#           ██   ██ ██   ██ ██    ██ ██      ██      ██      ██                #
#           ██████  ██████  ██    ██ ██      █████   ███████ ███████           #
#           ██      ██   ██ ██    ██ ██      ██           ██      ██           #
#           ██      ██   ██  ██████   ██████ ███████ ███████ ███████           #
#                                                                              #
################################################################################

function DefaultProcess {
    if [ "$fetch" -eq 1 ]; then
        TerminalTitle "Fetch - $config"

        declare -i start=$SECONDS
        Fetch
        duration=$(Format-Seconds "$((SECONDS - start))")

        AArrayUpdate stats fetch OK
        AArrayUpdate stats fetchDuration "$duration"
        echo "  -- Duration: $duration"
    fi

    if [ "$prepare" -eq 1 ]; then
        TerminalTitle "Prepare - $config"

        declare -i start=$SECONDS
        Prepare
        duration=$(Format-Seconds "$((SECONDS - start))")

        AArrayUpdate stats prepare OK
        AArrayUpdate stats prepareDuration "$duration"
        echo "  -- Duration: $duration"
    fi

    if [ "$build" -eq 1 ]; then
        TerminalTitle "Build - $config"

        declare -i start=$SECONDS
        Build
        duration=$(Format-Seconds "$((SECONDS - start))")

        AArrayUpdate stats build OK
        AArrayUpdate stats buildDuration "$duration"
        echo "  -- Duration: $duration"
    fi

    if [ "$test" -eq 1 ]; then
        TerminalTitle "Test - $config"

        declare -i start=$SECONDS
        Test
        duration=$(Format-Seconds "$((SECONDS - start))")

        AArrayUpdate stats test OK
        AArrayUpdate stats testDuration "$duration"
        echo "  -- Duration: $duration"
    fi
}

function Finalise {
    echo "Output Stats:"
    for pair in "${stats[@]}"; do
        key="${pair%:*}"
        value="${pair#*:}"
        echo "AArrayUpdate stats \"$key\" \"$value\""
    done

    Fill "_   " | Right " EOF "
}