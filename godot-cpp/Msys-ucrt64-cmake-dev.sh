#!/bin/bash

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Env Settings"
    envRun="/msys2_shell.cmd -ucrt64 -defterm -no-start -where $targetRoot -c"
    envActions="Msys-actions.sh"
    # envClean="CleanLog-gcc-cmake"
    echo "    run command   = $envRun"
    echo "    action script = $envActions"
    echo "    clean action  = $envClean"
    return
fi


gitUrl="https://github.com/enetheru/godot-cpp.git"
gitBranch="dev_tag"

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; fi
    if [ "$verbose" -eq 1 ]; then doVerbose="--verbose"; fi

    # scons target=template_debug debug_symbols=yes"
    buildType="RelWithDebInfo"
    buildConfig="-DCMAKE_BUILD_TYPE=$buildType"

    buildDir="$buildRoot/cmake-build-$buildType"
    mkdir -p "$buildDir" && cd $buildDir || return 1

    Format-Eval "cmake $doFresh .. -GNinja $buildConfig"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"

    # scons target=template_debug dev_build=yes"
    buildType="Debug"
    buildConfig="-DCMAKE_BUILD_TYPE=$buildType"
    
    buildDir="$buildRoot/cmake-build-$buildType"
    mkdir -p "$buildDir" && cd $buildDir || return 1
    
    Format-Eval "cmake $doFresh .. -GNinja $buildConfig -DGODOT_DEV_BUILD=YES"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"

    # scons target=template_debug dev_build=yes debug_symbols=no"
    buildType="Release"
    buildConfig="-DCMAKE_BUILD_TYPE=$buildType"

    buildDir="$buildRoot/cmake-build-$buildType"
    mkdir -p "$buildDir" && cd $buildDir || return 1

    Format-Eval "cmake $doFresh .. -GNinja -DGODOT_DEV_BUILD=YES"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"
}
