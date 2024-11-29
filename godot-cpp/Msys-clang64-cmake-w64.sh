#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

msysEnv="clang64"
declare buildDir

function Prepare {
    PrepareCommon

    buildDir="$buildRoot/cmake-build"
    mkdir -p "$buildDir" || return 1
    cd "$buildDir" || return 1

    Format-Command "cmake ../ -GNinja -DTEST_TARGET=template_release"
    cmake ../ -GNinja -DTEST_TARGET=template_release

}

function Build {
    H1 "CMake Build"

    cd "$buildDir" || return 1

    Format-Eval "cmake --build . --verbose -t godot-cpp-test --config Release"
    cmake --build . --verbose -t godot-cpp-test --config Release
}

function Test {
    TestCommon
}
