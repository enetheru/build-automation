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
    H1 "SCons Build"
    cd "$buildRoot/test" || return 1
    scons verbose=yes target=template_release
}

function Test {
  TestCommon
}
