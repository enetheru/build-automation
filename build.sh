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
   echo "Syntax: ./build.sh [-hfcbt] [--longopts] <target> [\"regexFilter\"]"
}

Help()
{
   # Display Help
   echo "My Little helper script to automate building things for different architectures"
   echo
   Syntax
   echo "options:"
   echo "  h, --help      Print this help"
   echo
   echo "  f, --fetch     Fetch the source"
   echo "  c, --configure Configure the source"
   echo "  b, --build     Build the code"
   echo "  t, --test      Test the code"
   echo
   echo "     --fresh     Re-Fresh the configuration before building"
   echo "     --append    Append to the log rather than clobber it"
   echo
   echo "     --match     Regex pattern matching script name"
   echo
   exit
}

# Option parsing pulled from this Stack Overflow Answer from Adam Katz
# https://stackoverflow.com/a/28466267
die() { echo "$*" >&2; exit 2; }  # complain to STDERR and exit with error
needs_arg() { if [ -z "$OPTARG" ]; then die "No arg for --$OPT option"; fi; }

# Defaults
fetch=0
configure=0
build=0
test=0

fresh=
logAppend=0
regexFilter=".*"

while getopts :hfan-: OPT; do  # allow -a, -b with arg, -c, and -- "with arg"
    # support long options: https://stackoverflow.com/a/28466267/519360
    if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
        OPT="${OPTARG%%=*}"       # extract long option name
        OPTARG="${OPTARG#"$OPT"}" # extract long option argument (may be empty)
        OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
    fi
    # shellcheck disable=SC2034
    case "$OPT" in
        h | help )      Help ;;
        f | fetch )     fetch=1 ;;
        c | configure ) configure=1 ;;
        b | build )     build=1 ;;
        t | test )      test=1 ;;
        fresh )         fresh="--fresh" ;;
        append )        logAppend=1 ;;
        match )         needs_arg; regexFilter="$OPTARG" ;;
        # c | charlie )  charlie="${OPTARG:-$charlie_default}" ;;  # optional argument
        \? )           exit 2 ;;  # bad short option (error reported via getopts)
        * )            die "Illegal option --$OPT" ;;            # bad long option
    esac
done
shift $((OPTIND-1)) # remove parsed options and args from $@ list

# Last minute checking of help flag before continuing.
if echo "${@}" | grep -qEe "--help|-h"; then
    Help
fi

if [ $fetch -eq 0 ] && [ $configure -eq 0 ] && [ $build -eq 0 ] && [ $test -eq 0 ]; then
    fetch=1
    configure=1
    build=1
    test=1
fi

H2 " Options "
echo "  root        = $root"
echo "  command     = ${argv[*]}"
echo
echo "  fetch       = $fetch"
echo "  configure   = $configure"
echo "  build       = $build"
echo "  test        = $test"
echo
echo "  fresh       = $fresh"
echo "  append      = $logAppend"
echo
echo "  match       = $regexFilter"

if [ -z "$1" ]; then
    echo
    Syntax
    Error "The <target> parameter is missing"
    exit 1
else
    target=$1
    echo "  target      = $target"
    shift 1
fi

if [ -z "$1" ]; then
    echo
    Syntax
    Error "The <branch> parameter is missing"
    exit 1
else
    gitBranch=$1
    echo "  gitBranch   = $gitBranch"
    shift 1
fi

Fill "- " | Center " Automatic "
platform=$(basename "$(uname -o)")
targetRoot="$root/$target"
mainScript="$root/$target/$platform-build.sh"
echo "  platform    = $platform"
echo "  root        = $root"
echo "  targetRoot  = $targetRoot"
echo "  script      = $mainScript"
echo

## Run target build script ##
# shellcheck disable=SC1090
source "$mainScript"
