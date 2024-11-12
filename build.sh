#!/bin/zsh
set -Ee

RED='\033[0;31m'
NC='\033[0m' # No Color

if [ "$(which rg)" = "rg not found" ]; then
    echo "${RED}Error: Unable to find Ripgrep${NC}"
    exit 1
fi
ripgrepVersion=$(rg -V)
if [ ! "${ripgrepVersion:0:7}" = "ripgrep" ]; then
    echo "${RED}Error: found rg is not RipGrep${NC}"
    exit 1
fi

echo 
echo " == Build-Automation =="
root=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "  root        = $root"


Syntax()
{
   echo "Syntax: ./build.sh [-hfa] [--longopts] <target> [\"regexFilter\"]"
}

Help()
{
   # Display Help
   echo "Add description of the script functions here."
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
# shellcheck disable=SC2317
needs_arg() { if [ -z "$OPTARG" ]; then die "No arg for --$OPT option"; fi; }

# Defaults
fresh=
logAppend=0
doTest=0

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
        f | fresh )    fresh=--fresh ;;
        a | append )   logAppend=1 ;;
        n | no-test )  doTest=1 ;;
        # b | bravo )    needs_arg; bravo="$OPTARG" ;;
        # c | charlie )  charlie="${OPTARG:-$charlie_default}" ;;  # optional argument
        \? )           exit 2 ;;  # bad short option (error reported via getopts)
        * )            die "Illegal option --$OPT" ;;            # bad long option
    esac
done
shift $((OPTIND-1)) # remove parsed options and args from $@ list

# Last minute checking of help flag before continuing.
if echo "${argv[@]}" | rg -q -e "--help|-h"; then
    Help
fi

echo "  fresh       = $fresh"
echo "  append      = $logAppend"

if [ -z "${argv[1]}" ]; then
    echo
    echo "${RED}Error: The <target> parameter is missing${NC}"
    echo
    Syntax
    die
else
    target=${argv[1]}
    echo "  target      = $target"
    targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
    targetRoot+="/$target"
    echo "  targetRoot  = $targetRoot"
    shift 1
fi

# TODO This logic is trash
if [ -n "${argv[1]}" ]; then
    pattern="${argv[1]}"
    if [ "$pattern" = "--" ]; then
        unset pattern
        shift 1
        echo "  Remaining arg: ${argv[*]}"
    else
        echo "  pattern     = $pattern"
    fi
fi

platform=$(uname -o)
echo "  uname -om   = $OS"

mainScript="$root/$target/$platform-build.sh"
echo "  script      = $mainScript"
echo

## Run target build script ##
source build-common.sh
source "$mainScript" "$pattern"
