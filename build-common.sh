#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi


# Fill Command
# Looks like using printf is the canonical way of repeating characters in a
# posix shell that is also performant - https://stackoverflow.com/a/30288267
Fill () {
    local filler="${1:- }"
    local width="${2:-$COLUMNS}" 
    local line="$(printf -- "%.0s$filler" {1..$width})"
    if [ ${#line} -ge $width ]; then
        printf "${line:0:$width}\n";
    else
        printf "$line\n"
    fi
}

Center(){
    local string=${1:-"Center"}
    local line="${2:-$(Fill)}"
    while read -t 0 line; do break; done

    local pos=$(( (${#line} - ${#string}) / 2 ))
    sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
}

Right(){
    local string=${1:-"Right"}
    local line="${2:-$(Fill)}"
    while read -t 0 line; do break; done

    local pos=$(( (${#line} - ${#string}) -1 ))
    sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
}

function H1 { figlet "$1" }
function H2 { echo; Center " $1 "; Fill =; }
function H3 { printf " == $1 ==\n" }

godot="$root/godot/macos-master/bin/godot.macos.editor.arm64"
godot_tr="$root/godot/macos-master-tr/bin/godot.macos.template_release.arm64"

# https://mharrison.org/post/bashfunctionoverride/
# Usage: RenameFunction <oldname> <newname>
function RenameFunction() {
    local ORIG_FUNC=$(declare -f $1)
    local NEWNAME_FUNC="$2${ORIG_FUNC#$1}"
    eval "$NEWNAME_FUNC"
}

function Fetch () {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    H1 Fetch
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
    echo
}

function Build () {
    echo
}

function Test () {
    echo
}

function Clean () {
    echo
}


