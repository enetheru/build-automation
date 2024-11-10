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

    if [ ! -d $buildRoot ]; then
        echo "  --Creating ${buildRoot}"
        mkdir -p $buildRoot
    fi

    #BASH files=$(shopt -s nullglob; shopt -s dotglob; echo /MYPATH/*)
    if [ ! $buildRoot(N/F) ]; then #ZSH Globbing qualifiers
        echo "  --Cloning ${target}"
        git clone "$gitUrl" "$buildRoot"
    fi

    # Change working directory
    cd "$buildRoot"

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if [ -n "$gitBranch" ]; then
        git checkout "$gitBranch"
    fi

    #TODO fix when the tree diverges and needs to be clobbered.
}

function Build () {
    echo "Build - Nothing to do"
}

function Clean () {
    echo "Clean - Nothing to do"
}


