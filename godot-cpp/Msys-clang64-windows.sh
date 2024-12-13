#!/bin/bash

set -e          # error and quit when( $? != 0 )
set -u          # error and quit on unbound variable
set -o pipefail # halt when a pipe failure occurs
#set -x          # execute and print

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# tell the build command how to run ourselves.
if [ "${1:-}" = "get_env" ]; then
    runArgs=(
        "-clang64"
        "-defterm"
        "-no-start"
        "-where $targetRoot"
    )
    envRun="/msys2_shell.cmd ${runArgs[*]} -c"
    gitBranch="msys2-clang64"
    return
fi


buildDir="$buildRoot/cmake-build"

function Prepare {

    H1 "Prepare"

    EraseFiles "editor_plugin_registration" "o|obj"

    H3 "CMake Configure"
    doFresh=''
    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; fi

    # Create Build Directory
    if [ ! -d "$buildDir" ]; then
        H4 "Creating $buildDir"
        Format-Eval "mkdir -p $buildDir"
    fi
    cd "$buildDir" || exit 1

    # CMake Configure
    cmakeVars=(
        '-G"Ninja"'
        "-DCMAKE_BUILD_TYPE=Release"
        "-DGODOT_ENABLE_TESTING=YES"
    )

    Format-Eval "cmake $doFresh .. ${cmakeVars[*]}"

    unset cmakeVars
}

function Build {
    statArray=( "target duration size" )

    sconsVars=(
        "use_mingw=yes"
        "use_llvm=yes"
    )

    EraseFiles "libgdexample" "dll"

    cd "$buildRoot/test" || return 1
    BuildSCons

    EraseFiles "libgdexample" "dll"

    cd "$buildRoot/cmake-build" || return 1
    BuildCMake

    H3 "sub-target summary"
    printf "%s\n" "${statArray[@]}" | column -t
}

