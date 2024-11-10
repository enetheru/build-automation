#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# Stubs for building code.

GODOT="${GODOT:-godot.macos.editor.arm64}"
GODOT_TR="${GODOT_TR:-godot.macos.template_release.arm64}"

function Source () {
    echo
    echo " == Source Code =="
    echo "  Target Root   = $targetRoot"
    echo "  Build Root    = $buildRoot"
    echo "  Git URL       = $gitUrl"
    echo "  Git Branch    = $gitBranch"
    return

    if [ ! -d $buildRoot ]; then
        mkdir -p $buildRoot
    fi


    if [ ! -z $( ls -A "$buildRoot" ) ]; then
        echo "  --Cloning ${target}"
        git clone $branch "$gitUrl" "$buildRoot"
    fi

    # Change working directory
    cd "$buildRoot"

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if [ -n "$gitBranch" ]; then
        git checkout "$gitBranch"
    fi
    return

    #TODO fix when the tree diverges and needs to be clobbered.
}

function Build () {
    echo "Build - Nothing to do"
}

function Clean () {
    echo "Clean - Nothing to do"
}


