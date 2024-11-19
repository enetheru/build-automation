#!/bin/bash
set -Ee

# The root is wherever this script is
root=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )

# Set Columns width, and source the formatting script
# shellcheck disable=SC2034
columns=120
source "$root/share/format.sh"

H1 "AutoBuild"

argv[0]="$0"
argv+=("${@}")

Syntax()
{
   echo "Syntax: ./build.sh [-hfa] [--longopts] <target> [\"regexFilter\"]"
}

Help()
{
   # Display Help
   echo "My Little helper script to automate building things for different architectures"
   echo
   Syntax
   echo "options:"
   echo "  h, --help      Print this help"
   echo "  f, --fresh     Re-Fresh the configuration before building"
   echo "  a, --append    Append to the log rather than clobber it"
   echo "  n, --no-test   Don't perform testing after build is completed"
   echo
   exit
}

# Option parsing pulled from this Stack Overflow Answer from Adam Katz
# https://stackoverflow.com/a/28466267
die() { echo "$*" >&2; exit 2; }  # complain to STDERR and exit with error
needs_arg() { if [ -z "$OPTARG" ]; then die "No arg for --$OPT option"; fi; }

# Defaults
fresh=
logAppend=0
doTest=1

while getopts :hfan-: OPT; do  # allow -a, -b with arg, -c, and -- "with arg"
    # support long options: https://stackoverflow.com/a/28466267/519360
    if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
        OPT="${OPTARG%%=*}"       # extract long option name
        OPTARG="${OPTARG#"$OPT"}" # extract long option argument (may be empty)
        OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
    fi
    # shellcheck disable=SC2034
    case "$OPT" in
        h | help )     Help ;;
        f | fresh )    fresh="--fresh" ;;
        a | append )   logAppend=1 ;;
        n | no-test )  doTest=0 ;;
        # b | bravo )    needs_arg; bravo="$OPTARG" ;;
        # c | charlie )  charlie="${OPTARG:-$charlie_default}" ;;  # optional argument
        \? )           exit 2 ;;  # bad short option (error reported via getopts)
        * )            die "Illegal option --$OPT" ;;            # bad long option
    esac
done
shift $((OPTIND-1)) # remove parsed options and args from $@ list

# Last minute checking of help flag before continuing.
if echo "${argv[@]}" | grep -qEe "--help|-h"; then
    Help
fi

H2 " Options "
echo "  root        = $root"
echo "  command     = ${argv[*]}"
echo "  fresh       = $fresh"
echo "  append      = $logAppend"
echo "  test        = $doTest"

argv=("${@}")

if [ -z "${argv[0]}" ]; then
    echo
    Syntax
    Error "The <target> parameter is missing"
    exit 1
else
    target=${argv[0]}
    echo "  target      = $target"
    shift 1
fi

# get the regex pattern from the second argument
if [ -n "${argv[1]}" ]; then
    pattern="${argv[1]}"
    if [ "$pattern" = "--" ]; then
        unset pattern
        shift 1
        echo "  Remaining arg: ${argv[*]}"
    fi
fi
echo "  regexFilter = $pattern"

#Center " Automatic " "$(Fill "- " )"
Fill "- " | Center " Automatic "

platform=$(basename "$(uname -o)")
echo "  platform    = $platform"

targetRoot="$root/$target"
echo "  targetRoot  = $targetRoot"

mainScript="$root/$target/$platform-build.sh"
echo "  script      = $mainScript"
echo

## Run target build script ##
# shellcheck disable=SC1090
source "$mainScript" "$pattern"
