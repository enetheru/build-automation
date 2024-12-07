#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Use default Env Settings"
    return
fi

gitUrl="https://github.com/enetheru/godot-cpp.git"
gitBranch="master"

function Prepare {
    PrepareCommon

    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; fi

    buildDir="$buildRoot/cmake-build-$buildType"
    mkdir -p "$buildDir" && cd $buildDir || return 1

    declare -a cmakeVars
    cmakeVars=("-DCMAKE_BUILD_TYPE=Release")
    # cmakeVars+=("-DGODOT_ENABLE_TESTING=ON")
    Format-Eval "cmake $doFresh .. -GNinja ${cmakeVars[@]}"
}

function Build {
    H1 "CMake Build"
    if [ "$verbose" -eq 1 ]; then doVerbose="--verbose"; fi

    cd $buildDir || return 1

    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"
}

function Test {
  TestCommon
}
