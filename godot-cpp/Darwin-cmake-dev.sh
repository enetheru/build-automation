#!/bin/zsh

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Env Settings"
    envRun="$SHELL -c"
    envActions="Darwin-actions.sh"
    envClean="CleanLog-macos-cmake"
    echo "    run command   = $envRun"
    echo "    action script = $envActions"
    return
fi

gitUrl="https://github.com/enetheru/godot-cpp.git"
gitBranch="dev_tag"

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    if [ "$fresh" -eq 1 ]; then; doFresh="--fresh"; fi
    doVerbose="$(if [ "$verbose" -eq 1 ]; then echo "--verbose"; fi)"

    # scons target=template_debug debug_symbols=yes"
    buildDir="$buildRoot/cmake-build-RelWithDebInfo"
    mkdir -p "$buildDir" && cd $buildDir || return 1

    Format-Eval "cmake $doFresh .. -GNinja -DCMAKE_BUILD_TYPE=RelWithDebInfo"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"

    # scons target=template_debug dev_build=yes"
    buildDir="$buildRoot/cmake-build-Debug"
    mkdir -p "$buildDir" && cd $buildDir || return 1
    
    Format-Eval "cmake $doFresh .. -GNinja -DCMAKE_BUILD_TYPE=Debug -DGODOT_DEV_BUILD=YES"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"

    # scons target=template_debug dev_build=yes debug_symbols=no"
    buildDir="$buildRoot/cmake-build-Release"
    mkdir -p "$buildDir" && cd $buildDir || return 1

    Format-Eval "cmake $doFresh .. -GNinja -DCMAKE_BUILD_TYPE=Release -DGODOT_DEV_BUILD=YES"
    Format-Eval "cmake --build . -j 7 $doVerbose -t godot-cpp-test"
}
