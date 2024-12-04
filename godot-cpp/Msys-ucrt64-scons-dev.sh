#!/bin/bash

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Env Settings"
    envRun="/msys2_shell.cmd -ucrt64 -defterm -no-start -where $targetRoot -c"
    envActions="Msys-actions.sh"
    envClean="CleanLog-gcc-scons"
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
    H1 "SCons Build"
    if [ "$verbose" -eq 1 ]; then
        doVerbose="verbose=yes"
    fi

    H4 "Changing directory to $buildRoot/test"
    cd "$buildRoot/test" || return 1

    target="target=template_debug"
    buildProfile="build_profile=build_profile.json"
    sconsOptions="$doVerbose $target $buildProfile use_mingw=yes"

    # build with dev_build=yes
    Format-Eval "scons $sconsOptions debug_symbols=yes"

    # build with dev_build=yes
    Format-Eval "scons $sconsOptions dev_build=yes"

    # build with dev_build=yes debug_symbols=no
    Format-Eval "scons $sconsOptions dev_build=yes debug_symbols=no"
}
