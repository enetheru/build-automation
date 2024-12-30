#!/usr/bin/env bash

# Require Dot Sourcing Script.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) || (echo "format.sh needs to be sourced."; exit 1)

# Dot Source Guard
if [ -n "${SOURCE_FORMAT_SH:-}" ] ; then return; fi
readonly SOURCE_FORMAT_SH=1

columns=${columns:-$(tput cols)}
RED='\033[0;31m'
ORANGE='\033[0;93m'
NC='\033[0m' # No Colo

function TerminalTitle {
  echo -ne "\033]0;$1\007"
}

function use-line {
    local line
    read -r line
    $1 "$line"
}

# MARK: FORMAT
###################################- Format -###################################
#                                                                              #
#             ███████  ██████  ██████  ███    ███  █████  ████████             #
#             ██      ██    ██ ██   ██ ████  ████ ██   ██    ██                #
#             █████   ██    ██ ██████  ██ ████ ██ ███████    ██                #
#             ██      ██    ██ ██   ██ ██  ██  ██ ██   ██    ██                #
#             ██       ██████  ██   ██ ██      ██ ██   ██    ██                #
#                                                                              #
################################################################################

# Simplest to read from all the junk surrounding this question.
# https://stackoverflow.com/a/51268514
# I would use numfmt --to=iec $1; but its not available on macos.
function Format-Bytes {
    declare -i num=${1:-0}
    suffix=( "B" "K" "M" "G" "T" "P" "E" "Z" "Y" )
    index=0
    while [ $num -gt 1024 ]; do
        num=$(( num / 1024 ))
        index=$((index+1))
    done
    printf "%0d%s"  "$num" "${suffix[$index]}"
}

function Format-Seconds {
    declare -i num=${1:-0}
    declare -a divisors=( 60 60 24 7 30 365 )

    if [ ${#num} -lt 3 ]; then
        echo "${num}s"
        return
    fi

    declare -a comp=()
    dSize=${#divisors[@]}
    for (( i=0; i<dSize; i++ )); do
        d=${divisors[$i]}
        if [ $num -gt "$d" ]; then
            div=$(( num / d ))      # Dividend
            rem=$(( num - div * d)) # Remainder
            comp+=("$rem")
            num=$div
            continue
        fi
        break
    done
    #remainder
    comp+=("$num")

    # Join everything together.
    declare -a suffix=( "s" "m" "h" "d" "w" "m" "y")
    cSize=${#comp[@]}
    declare result=""
    for (( i=cSize-1; i>=0; i-- )); do
        result+=$(printf "%d%s"  "${comp[i]}" "${suffix[i]}")
    done

    echo "$result"
}

function Figlet {
    local customFiglet=/c/git/cmatsuoka/figlet/figlet

    local message="${1:-Figlet}" font="${2:-standard}" align="${3:-}"

    # other figlet fonts I like are 'big','standard','small','Ogre',
    # 'Stronger Than All' and 'ANSI Regular'
    local options=(
        "$align"
        "-f $font"
        "-w $columns"
        "$message")
    if [ "$(command -v figlet)" ]; then
        eval "figlet ${options[*]}"
    elif [ -f "$customFiglet" ];then
        eval "$customFiglet ${options[*]}"
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
    local string="${1:-Center}" line
    if [ -z "${2:-}" ]; then
        read -r line
    else
        line="$2"
    fi

    declare -i pos=$(( (${#line} - ${#string}) / 2 ))
    if [ $pos -le 0 ]; then
        printf -- "%s\n" "$string"
    else
#        echo "$string"
        sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1 ${string} \2/" <<< "${line}"
    fi
}

function Right {
    set -- "${1:-Right}" "${2:-}"
    local string="$1" line

    if [ -z "$2" ]; then
        read -r line
    else
        line="$2"
    fi

    local pos=$(( ${#line} - ${#string} ))

    if [ $pos -lt 0 ]; then
        printf "%s" "$string"
    else
        sed -E "s/^(.{$pos}).{${#string}}(.*$)/\1$string\2/" <<< "$line"
    fi
}

##################################- Headings -##################################
#                                                                            #
#       ██   ██ ███████  █████  ██████  ██ ███    ██  ██████  ███████        #
#       ██   ██ ██      ██   ██ ██   ██ ██ ████   ██ ██       ██             #
#       ███████ █████   ███████ ██   ██ ██ ██ ██  ██ ██   ███ ███████        #
#       ██   ██ ██      ██   ██ ██   ██ ██ ██  ██ ██ ██    ██      ██        #
#       ██   ██ ███████ ██   ██ ██████  ██ ██   ████  ██████  ███████        #
#                                                                            #
################################################################################

function H1 {
  Figlet "$1" "big" "-c"
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

function H5 {
  printf "  -- %s\n" "$1"
}

##################################- Command -###################################
#                                                                            #
#       ██████  ██████  ███    ███ ███    ███  █████  ███    ██ ██████       #
#      ██      ██    ██ ████  ████ ████  ████ ██   ██ ████   ██ ██   ██      #
#      ██      ██    ██ ██ ████ ██ ██ ████ ██ ███████ ██ ██  ██ ██   ██      #
#      ██      ██    ██ ██  ██  ██ ██  ██  ██ ██   ██ ██  ██ ██ ██   ██      #
#       ██████  ██████  ██      ██ ██      ██ ██   ██ ██   ████ ██████       #
#                                                                            #
################################################################################

function Format-Command {
  printf "\n  :%s\n  󰞷 %s\n" "$(pwd)" "$1"
}

function Format-Eval {
  echo
  printf "  󰝰:%s\n" "$(pwd)"
  printf "  󰞷 %s\n" "$1"
  eval "$1"
  return $?
}

function Warning {
  printf "\n${ORANGE}Warning: %s${NC}\n" "$1"
}

function Error {
  printf "\n${RED}Error: %s${NC}\n" "$1"
}

# Log re-formatting for easy comparison
function CleanLog-Default {
    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern "$1" | sed -E 's/ +/\n/g' \
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D'
}

function CleanLog-macos-scons {
    # Cleanup Logs
    keep='  󰞷 scons|^ranlib|^ar rc|memory.cpp|Cocoa|libgdexample'
    joins="-o|-arch|-framework|-t|-j|-MT|-MF|-isysroot|-install_name|ar"
    scrub="\[[0-9]+\/[0-9]+\]|&&|:|󰞷|build_profile"
    splits="^scons|^clang|^ranlib|^ar"
    rg -M2048 "$keep" "$1" \
        | sed -E "s/ +/\n/g" \
        | sed -E ":start
            \$!N; s/($joins)\n/\1 /;t start
            P;D" \
        | sed -E "/$scrub/d" \
        | sed -E "s/($splits)/\n\1/" \
        | sed 'N; /^\n$/d;P;D'
}

function CleanLog-macos-cmake {
    # Cleanup Logs
    keep='  󰞷 cmake|^ranlib|memory.cpp|Cocoa|libgdexample'
    scrub="\[[0-9]+\/[0-9]+\]|&&|:|󰞷"
    joins="-o|-arch|-framework|-t|-j|-MD|-MT|-MF|-isysroot|-install_name"
    rg -M2048 "$keep" "$1" \
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

function CleanLog-ucrt-scons {
    # Cleanup Logs
    keep='  󰞷 scons|^ranlib|^ar rc|memory.cpp|Cocoa|libgdexample'
    joins="-o|-arch|-framework|-t|-j|-MT|-MF|-isysroot|-install_name|ar"
    scrub="\[[0-9]+\/[0-9]+\]|&&|:|󰞷|build_profile"
    splits="^scons|^clang|^ranlib|^ar"
    rg -M2048 "$keep" "$1" \
        | sed -E "s/ +/\n/g" \
        | sed -E ":start
            \$!N; s/($joins)\n/\1 /;t start
            P;D" \
        | sed -E "/$scrub/d" \
        | sed -E "s/($splits)/\n\1/" \
        | sed 'N; /^\n$/d;P;D'
}

function CleanLog-ucrt-cmake {
    # Cleanup Logs
    keep='  󰞷 cmake|^ranlib|^ar rc|memory.cpp|Cocoa|libgdexample'
    joins="-o|-arch|-framework|-t|-j|-MT|-MF|-isysroot|-install_name|ar"
    scrub="^\[[0-9]+\/[0-9]+\]|^&&|^:|^󰞷|^build_profile|^-MD|^-MT|^-MF"
    splits="^cmake|^ranlib|^ar"
    sed -E 's/&&/\n/g' "$1"\
        | rg -M2048 "$keep" \
        | sed -E "s/ +/\n/g" \
        | sed -E ":start
            \$!N; s/($joins)\n/\1 /;t start
            P;D" \
        | sed -E "/$scrub/d" \
        | sed -E "s/($splits)/\n\1/" \
        | sed 'N; /^\n$/d;P;D'
}


function CleanLog-gcc-scons {
    # Cleanup Logs
    keep=' scons|gcc-ar q|memory.cpp|libgdexample'
    joins="-o|-arch|-framework|-t|-j|-MT|-MF|-isysroot|-install_name|ar"
    scrub="^\[[0-9]+\/[0-9]+\]|^&&|^:|󰞷|^build_profile|^-MD|^-MT|^-MF"
    splits="mingw32-"
    sed -E 's/&&/\n/g' "$1"\
        | cut -c 1-1024 \
        | sed -En "/$keep/p" \
        | sed -E "s/ +/\n/g" \
        | sed -E ":start
            \$!N; s/($joins)\n/\1 /;t start
            P;D" \
        | sed -E "/$scrub/d" \
        | sed -E "/($splits)/{x;p;x;}" \
        | sed 'N; /^\n$/d;P;D'
}

##################################- Aggregate -#################################
#                                                                              #
#  █████   ██████   ██████  ██████  ███████  ██████   █████  ████████ ███████  #
# ██   ██ ██       ██       ██   ██ ██      ██       ██   ██    ██    ██       #
# ███████ ██   ███ ██   ███ ██████  █████   ██   ███ ███████    ██    █████    #
# ██   ██ ██    ██ ██    ██ ██   ██ ██      ██    ██ ██   ██    ██    ██       #
# ██   ██  ██████   ██████  ██   ██ ███████  ██████  ██   ██    ██    ███████  #
#                                                                              #
################################################################################

# TODO re-implement this for bash
#function BigBox {
#    local message="${1:-Figlet}" font="${2:-standard}" align="${3:-}"
#
#    # Get title from stdin stream
#    set -- "${1:-}" "${2:-}"
#    local title="$1" line
#
#    if [ -z "$2" ]; then
#        read -r line
#    else
#        line="$2"
#    fi
#
#    # Top Line and Space
#    Fill '#' | Center "- $title -"
#    Right '#' | Left ' #'
#
#    figlet -l -f "ANSI Regular" "$title"
#    Fill | Center | Left ' #' | Right '#'
#
#    # Bottom Space and Line
#    Right '#' | Left ' #'
#    Fill '#'
#}