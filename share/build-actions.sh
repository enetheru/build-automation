#!/bin/bash
# shellcheck disable=SC2154

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# https://mharrison.org/post/bashfunctionoverride/
# Usage: RenameFunction <old-name> <newname>
function RenameFunction {
    local ORIG_FUNC
    ORIG_FUNC=$(declare -f "$1")
    local NEWNAME_FUNC="$2${ORIG_FUNC#"$1"}"
    eval "$NEWNAME_FUNC"
}

function Fetch {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    H1 "Git Fetch"

    echo "  Target Root   = $targetRoot"
    echo "  Build Root    = $buildRoot"
    echo "  Git URL       = $gitUrl"
    echo "  Git Branch    = $gitBranch"

    # Clone to bare repo if not already
    if [ ! -d "$targetRoot/git" ]; then
        Format-Eval "git clone --bare \"$gitUrl\" \"$targetRoot/git\""
    fi

    # Checkout worktree if not already
    if [ ! -d "$buildRoot" ]; then
        Format-Eval "git --git-dir \"$targetRoot/git\" worktree add -d \"$buildRoot\""
    fi

    # Update worktree
    cd "$buildRoot" || return 1
    Format-Eval "git reset --hard"
    Format-Eval "git checkout -d $gitBranch"
    Format-Eval "git status"
}

function Prepare {
    echo
}

function Build {
    echo
}

function Test {
    echo
}

function Clean {
    echo
}

function CleanLog-Default {
    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern "$1" | sed -E 's/ +/\n/g' \
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D'
}

function CleanLog-macos {
    # Cleanup Logs
    keep='  󰞷 cmake|^ranlib|memory.cpp|Cocoa|libgdexample'
    scrub="\[[0-9]+\/[0-9]+\]|&&|:|󰞷"
    joins="-o|-arch|-framework|-t|-j|-MT|-MF|-isysroot|-install_name|Omitted|long|matching"
    rg -M2048 $keep "$1" \
        | sed -E ":start
            s/ +/\n/g;t start
            s/$scrub//;t start" \
        | sed -E ":start
            \$!N
            s/($joins)\n/\1 /;t start
            P;D" \
        | sed "s/^cmake/\ncmake/" \
        | sed 'N; /^\n$/d;P;D'
}
