#!/bin/bash
#
# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Env Settings"
    envRun="/msys2_shell.cmd -ucrt64 -defterm -no-start -where $targetRoot -c"
    envActions="Msys-actions.sh"
    envClean="CleanLog-gcc"
    echo "    run command   = $envRun"
    echo "    action script = $envActions"
    echo "    clean action  = $envClean"
    return
fi

declare buildDir

function Prepare {
    PrepareCommon

    buildDir="$buildRoot/cmake-build"
    mkdir -p "$buildDir" || return 1
    cd "$buildDir" || return 1

    if [ "$fresh" -eq 1 ]; then doFresh="--fresh"; else unset doFresh; fi
    Format-Eval "cmake $doFresh .. -DTEST_TARGET=template_release"
}

function Build {
    H1 "CMake Build"

    cd "$buildDir" || return 1

    if [ "$verbose" -eq 1 ]; then doVerbose="--verbose"; else unset doVerbose; fi
    Format-Eval "cmake --build . $doVerbose --config Release"
}

function Test {
    TestCommon
}
