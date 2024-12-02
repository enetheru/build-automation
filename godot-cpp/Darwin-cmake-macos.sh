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
