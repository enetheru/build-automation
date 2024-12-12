#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# tell the build command how to run ourselves.
if [ "${1:-}" = "get_env" ]; then
    runArgs=(
        "-ucrt64"
        "-defterm"
        "-no-start"
        "-where $targetRoot"
    )
    envRun="/msys2_shell.cmd ${runArgs[*]} -c"
    gitBranch="Whacky"
    return
fi

function Fetch {
    H3 "No Fetch Action Specified"
    echo "-"
}