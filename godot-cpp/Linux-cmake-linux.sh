
# Compile the test project


#!/bin/bash
# shellcheck disable=SC2154
# Compile the test project

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

function Prepare {
    PrepareCommon

    cd "$buildRoot/cmake-build" || exit 1

    if [ -n "$fresh" ]; then
        doFresh="--fresh"
    fi

    H1 "CMake Configure"
    Format-Command "cmake $doFresh .. -GNinja"
    cmake $doFresh .. -GNinja
}

function Build {
    H1 "CMake Build"
    cd "$buildRoot/cmake-build" || return 1

    Format-Command "cmake --build . --verbose -t godot-cpp-test --config Release"
    cmake --build . -j 6 --verbose -t godot-cpp-test --config Release
}

function Test {
  TestCommon
}
