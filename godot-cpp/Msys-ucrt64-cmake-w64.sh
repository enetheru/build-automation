#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

msysEnv="ucrt64"

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    mkdir -p "$buildRoot/cmake-build"
    cd "$buildRoot/cmake-build" || return 1

    Format-Command "cmake ../ -GNinja -DTEST_TARGET=template_release"
    cmake ../ -GNinja -DTEST_TARGET=template_release

    Format-Command "cmake --build . --verbose -t godot-cpp-test --config Release"
    cmake --build . --verbose -t godot-cpp-test --config Release
}

function Test {
    TestCommon
}
