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
    Figlet "Git Fetch"

    H3 "Update WorkTree"
    # Checkout worktree if not already
    if [ ! -d "$buildRoot" ]; then
        Format-Eval "git --git-dir=\"$targetRoot/git\" worktree add -d \"$buildRoot\""
    fi

    # Update worktree
    cd "$buildRoot" || return 1
    Format-Eval "git checkout --force --detach $gitBranch"
    Format-Eval "git status"
    Fill "-"
}

function Prepare {
    H3 "No Prepare Action Specified"
    echo "-"
}

function Build {
    H3 "No Build Action Specified"
    echo "-"
}

function Test {
    H3 "No Test Action Specified"
    echo "-"
}

function Clean {
    H3 "No Clean Action Specified"
    echo "-"
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

#### Associative arrays ####
# Because macos is using a really old version of bash I cant use associative
# arrays in my base build script.

function AssocUpdate {
    # $1 = name of associative array variable
    # $2 = key
    # $3 = value
    # Syntax: AssocUpdate "container" "key" "value"
    # Will add keys if they don't exist already
    #
    #ingest the name of the array and copy the values.
    declare -a rows=($(eval "echo \"\${$1[@]}\""))
    key=${2:-}
    value=${3:-}

    size=$((${#rows[@]}-1))
    echo "size=$size"
    new=1
    index=0
    if [ $size -ge 0 ]; then
        for i in $(eval "echo {0..$size}"); do
            row="${rows[$i]}"
            echo "[$i]={ key=${row%:*}, value=${row#*:} }"
            if [ "$key" == "${row%:*}" ]; then
                new=0
                index=$i
                break
            fi
        done
    fi

    # Add new key
    if [ -n "$2" -a $new -eq 1 ]; then
        echo "$1+=(\"$2:$3\")"
        eval "$1+=(\"$2:$3\")"
    fi

    # Update key
    if [ -n "$2" -a $new -eq 0 ]; then
        echo "$1[$index]=\"$2:$3\""
        eval "$1[$index]=\"$2:$3\""
    fi
}
