#!/bin/bash

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ "$sourced" -eq 0 ]; then
    echo "Do not run this script directly, it simply holds formatting functions"
    exit
fi

columns=${columns:-$COLUMNS}
RED='\033[0;31m'
ORANGE='\033[0;93m'
NC='\033[0m' # No Color

function Figlet {
  local customFiglet=/c/git/cmatsuoka/figlet/figlet
  # other figlet fonts I like are 'standard','Ogre', 'Stronger Than All' and 'ANSI Regular'
  if [ "$(command -v figlet)" ]; then
    figlet "$1"
  elif [ -f "$customFiglet" ];then
    "$customFiglet" -f standard "$1"
  else
      echo "==== $1 ===="
  fi
}

# Fill Command
# Looks like using printf is the canonical way of repeating characters in a
# posix shell that is also performant - https://stackoverflow.com/a/30288267
function Fill {
    local filler="${1:- }"
    declare -i width=${2:-$columns}
    local line
    line=$(printf -- "%.0s$filler" $(seq $width))
    if [ ${#line} -ge $width ]; then

        printf -- "%s\n" "${line:0:$width}";
    else
        printf -- "%s\n" "$line"
    fi

}

function Center {
    local string line
    string="${1:-Center}"
    if [ -z "$2" ];
    then read -r line
    else line="$2"
    fi

    local pos=$(( (${#line} - ${#string}) / 2 ))
    if [ $pos -lt 0 ]; then
      printf -- "%s\n" "$string"
    else
      sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
    fi
}

function Right {
    local string line
    string=${1:-"Right"}
    if [ -z "$2" ];
    then read -r line
    else line="$2"
    fi

    local pos=$(( (${#line} - ${#string}) -1 ))
    if [ $pos -lt 0 ]; then
      printf "%s" "$string"
    else
      sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
    fi
}



function H1 {
  Figlet "$1"
}

function H2 {
#  printf "\n%s\n" "$(Center "- $1 -" "$(Fill "=")")"
  printf "\n%s\n" "$(Fill "=" |  Center "- $1 -")"
}

function H3 {
  printf "\n == %s ==\n" "$1"
}

function H4 {
  printf "  => %s\n" "$1"
}

function Format-Command {
printf "\n  :%s\n  󰞷 %s\n" "$(pwd)" "$1"
}

function Warning {
  printf "\n${ORANGE}Warning: %s${NC}\n" "$1"
}

function Error {
  printf "\n${RED}Error: %s${NC}\n" "$1"
}
