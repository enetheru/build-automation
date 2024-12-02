#!/bin/zsh

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Env Settings"
    envRun="$SHELL -c"
    envActions="Darwin-actions.sh"
    echo "    run command   = $envRun"
    echo "    action script = $envActions"
    return
fi

gitUrl="https://github.com/enetheru/godot-cpp.git"
gitBranch="dev_tag"
buildDebug=''
buildDev=''

function Prepare {
    PrepareCommon

    doFresh="$(if [ "$fresh" -eq 1 ]; then echo "--fresh"; fi)"

    buildDebug="$buildRoot/cmake-build-debug"
    mkdir -p "$buildDebug"

    buildDev="$buildRoot/cmake-build-dev"
    mkdir -p "$buildDev"

    cd $buildDebug || return 1
    Format-Eval "cmake $doFresh .."

    cd $buildDev || return 1
    Format-Eval "cmake $doFresh .. -DGODOT_DEV_BUILD=YES"
}

function Build {
    H1 "CMake Build"

    doVerbose="$(if [ "$verbose" -eq 1 ]; then echo "--verbose"; fi)"

    cd $buildDebug || return 1
    # scons target=template_debug debug_symbols=yes"
    Format-Eval "cmake --build . $doVerbose -t godot-cpp-test --config RelWithDebInfo"

    cd $buildDev || return 1
    # scons target=template_debug dev_build=yes"
    Format-Eval "cmake --build . $doVerbose -t godot-cpp-test --config Debug"

    # scons target=template_debug dev_build=yes debug_symbols=no"
    Format-Eval "cmake --build . $doVerbose -t godot-cpp-test --config Release"
}
