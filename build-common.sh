#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

# https://mharrison.org/post/bashfunctionoverride/
# Usage: RenameFunction <oldname> <newname>
function RenameFunction {
    local ORIG_FUNC=$(declare -f $1)
    local NEWNAME_FUNC="$2${ORIG_FUNC#$1}"
    eval "$NEWNAME_FUNC"
}

# Fill Command
# Looks like using printf is the canonical way of repeating characters in a
# posix shell that is also performant - https://stackoverflow.com/a/30288267
Fill () {
    local filler="${1:- }"
    local width="${2:-$COLUMNS}" 
    local line=$(printf -- "%.0s$filler" $(seq $width))
    if [ ${#line} -ge $width ]; then
        printf "${line:0:$width}\n";
    else
        printf "$line\n"
    fi
}

Center(){
    local string="${1:-Center}"
    local line="${2:-$(Fill)}"
    while read -t 0 line; do break; done

    local pos=$(( (${#line} - ${#string}) / 2 ))
    if [ $pos -lt 0 ]; then
      printf "%s" "$string"
    else
      sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
    fi

}

Right(){
    local string=${1:-"Right"}
    local line="${2:-$(Fill)}"
    while read -t 0 line; do break; done

    local pos=$(( (${#line} - ${#string}) -1 ))
    if [ $pos -lt 0 ]; then
      printf "%s" "$string"
    else
      sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
    fi
}

function Figlet {
  customFiglet=/c/git/cmatsuoka/figlet/figlet
  # other figlet fonts I like are 'standard','Ogre', 'Stronger Than All' and 'ANSI Regular'
  if [ $(command -v figlet) ]; then
    figlet "$1"
  elif [ -n "$customFiglet" ];then
    "$customFiglet" -f standard "$1"
  else
      echo "==== $1 ===="
  fi

}

function H1 {
  Figlet "$1"
}

function H2 {
  echo; Center " $1 "; Fill "=";
}

function H3 {
  printf "%s" " == $1 ==\n"
}

function Fetch {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    H1 Fetch
    echo "  Target Root   = $targetRoot"
    echo "  Build Root    = $buildRoot"
    echo "  Git URL       = $gitUrl"
    echo "  Git Branch    = $gitBranch"

    if [ ! -d "$buildRoot" ]; then
        echo "  --Creating ${buildRoot}"
        mkdir -p "$buildRoot"
    fi

    #BASH files=$(shopt -s nullglob; shopt -s dotglob; echo /MYPATH/*)
    #FIXME - its simply luck that this works, without zsh it evaluates to a string.
    if [ ! -d "$buildRoot" ]; then #ZSH Globbing qualifiers
        echo "  --Cloning ${target}"
        git clone "$gitUrl" "$buildRoot"
    fi

    # Change working directory
    cd "$buildRoot" || exit

    # Fetch any changes and reset to latest
    echo
    git fetch --all
    git reset --hard '@{u}'
    if [ -n "$gitBranch" ]; then
        git checkout "$gitBranch"
    fi

    #TODO fix when the tree diverges and needs to be clobbered.
    cd "$targetRoot" || exit
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