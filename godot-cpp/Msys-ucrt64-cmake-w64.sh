#!/bin/bash
# Compile the test project

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

msysEnv="ucrt64"

function Prepare {
    CommonPrep
}

function Build {
    H1 "CMake Build"

    mkdir -p "$buildRoot/cmake-build"
    cd "$buildRoot/cmake-build" || return 1

    cmake ../ -GNinja
    cmake --build . -t godot-cpp-test --config Release
}

function Test {
    CommonTest
}
