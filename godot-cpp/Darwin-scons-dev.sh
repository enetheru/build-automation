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

function Prepare {
    PrepareCommon
}

function Build {
    H1 "SCons Build"
    if [ "$verbose" -eq 1 ]; then
        doVerbose="verbose=yes"
    fi

    H4 "Changing directory to $buildRoot/test"
    cd "$buildRoot/test" || return 1

    target="target=template_debug"
    buildProfile="build_profile=build_profile.json"
    sconsOptions="$doVerbose $target $buildProfile"

    # build with dev_build=yes
    Format-Eval "scons $sconsOptions debug_symbols=yes"

    # build with dev_build=yes
    Format-Eval "scons $sconsOptions dev_build=yes"

    # build with dev_build=yes debug_symbols=no
    Format-Eval "scons $sconsOptions dev_build=yes debug_symbols=no"
}
