#!/bin/zsh

# tell the build command how to run ourselves.
if [ "$1" = "get_env" ]; then
    H4 "Using default environment"
    return
fi

function Build {
    H1 "Scons Build"

    if [ $jobs -gt 0 ]; then doJobs="-j $jobs"; else unset doJobs; fi
    if [ "$verbose" -eq 1 ]; then doVerbose="verbose=yes"; else unset doVerbose; fi

    cd "$buildRoot" || return 1

    targets=("template_debug" "template_release" "editor")
    for target in "${targets[@]}"; do
        Format-Eval "scons $doJobs $doVerbose target=$target"
    done
}
