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
}

function Build {
    H1 "CMake Build"

    cd "$buildRoot" || return 1

    mkdir -p cmake-build
    cd cmake-build || return 1

    # Configure
    cmake "$fresh" ../ -GNinja

    # Build
    cmake --build . -j 6 --verbose -t godot-cpp-test --config Release
}

function Test {
  TestCommon
}
