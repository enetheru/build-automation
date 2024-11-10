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
    local SOURCE_ORIGIN="$1"
    local SOURCE_BRANCH="$2"
    local BUILD_ROOT="$3"

    echo "== Source Code =="
    echo "Git URL: $SOURCE_ORIGIN"
    echo "Git Branch: $SOURCE_BRANCH"
    echo "Source Dest: $BUILD_ROOT"
    exit



    if [ ! -z $( ls -A "$BUILD_ROOT" ) ]; then
        if [ -n "$SOURCE_BRANCH" ]; then
            local BRANCH="-b $SOURCE_BRANCH"
        else
            BRANCH=
        fi
        git clone "$BRANCH" "$SOURCE_ORIGIN" "$BUILD_ROOT"
    fi

    # Change working directory
    cd "$BUILDROOT"

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if [ -n "$SOURCE_BRANCH" ]; then
        git checkout "$SOURCE_BRANCH"
    fi

    #TODO fix when the tree diverges and needs to be clobbered.
}

function Build () {
    echo "Build - Nothing to do"
}

function Clean () {
    echo "Clean - Nothing to do"
}


