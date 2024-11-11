#!/bin/bash
# Compile the test project

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

Prepare(){
    figlet Prepare

    cd $buildRoot
    mkdir -p cmake-build
}

Build(){
    figlet CMake

    cd cmake-build

    # Configure
    cmake $fresh ../ -GNinja

    # Build
    cmake --build . -j 6 --verbose -t godot-cpp-test --config Release
}
