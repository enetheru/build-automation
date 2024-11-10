#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

godot="$root/godot/macos-master/bin/godot.macos.editor.arm64"
godot_tr="$root/godot/macos-master-tr/godot.macos.template_release.arm64"

function Fetch () {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    figlet Fetch
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
    echo
    git fetch --all
    git reset --hard '@{u}'
    if [ -n "$gitBranch" ]; then
        git checkout "$gitBranch"
    fi

    #TODO fix when the tree diverges and needs to be clobbered.
    cd $targetRoot
}

function Prepare (){
    echo "Prepare - Nothing to do"
}

function Build () {
    echo "Build - Nothing to do"
}

function Test () {
    echo "Test - Nothing to do"
}

function Clean () {
    echo "Clean - Nothing to do"
}


