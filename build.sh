#!/bin/bash

# The root is wherever this script is
root=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )

# Set Columns width, and source the formatting script
# shellcheck disable=SC2034
columns=120
source "$root/share/format.sh"


argv[0]="$0"
argv+=("${@}")

Syntax()
{
   echo "Syntax: ./build.sh [-hfcbt] [--list] [--fresh] [--append] [--scriptFilter=<regex>] <target> [gitBranch]"
}

Help()
{
   # Display Help
   echo "My Little helper script to automate building things for different architectures"
   echo
   Syntax
   echo "options:"
   echo "  h, --help      Print this help"
   echo "     --list      Only liste the scripts"
   echo
   echo "  f, --fetch     Fetch the source"
   echo "  c, --configure Configure the source"
   echo "  b, --build     Build the code"
   echo "  t, --test      Test the code"
   echo
   echo "     --fresh     Re-Fresh the configuration before building"
   echo "     --append    Append to the log rather than clobber it"
   echo
   echo "     --scriptFilter=<regex> Regex pattern matching script name"
   echo
   exit
}

# Option parsing pulled from this Stack Overflow Answer from Adam Katz
# https://stackoverflow.com/a/28466267
die() { echo "$*" >&2; exit 2; }  # complain to STDERR and exit with error
needs_arg() { if [ -z "$OPTARG" ]; then Syntax; die "No arg for --$OPT option"; fi; }

# Defaults
verbose=1
list=0

fetch=0
configure=0
build=0
test=0

fresh=0
logAppend=0
scriptFilter=".*"

gitBranch=""

while getopts :hfcbt-: OPT; do  # allow -a, -b with arg, -c, and -- "with arg"
    # support long options: https://stackoverflow.com/a/28466267/519360
    if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
        OPT="${OPTARG%%=*}"       # extract long option name
        OPTARG="${OPTARG#"$OPT"}" # extract long option argument (may be empty)
        OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
    fi
    # shellcheck disable=SC2034
    case "$OPT" in
        h | help )      Help ;;
        list )          list=1 ;;
        f | fetch )     fetch=1 ;;
        c | configure ) configure=1 ;;
        b | build )     build=1 ;;
        t | test )      test=1 ;;
        fresh )         fresh=1 ;;
        append )        logAppend=1 ;;
        scriptFilter )  needs_arg; scriptFilter="$OPTARG" ;;
        # c | charlie )  charlie="${OPTARG:-$charlie_default}" ;;  # optional argument
        \? )           echo "Error: Bad short option" >&2; Syntax; exit 2 ;;  # bad short option (error reported via getopts)
        * )            die "Illegal option --$OPT" ;;            # bad long option
    esac
done
shift $((OPTIND-1)) # remove parsed options and args from $@ list

# Last minute checking of help flag before continuing.
if echo "${@}" | grep -qEe "--help|-h"; then
    Help
fi

H1 "AutoBuild"

if [ $fetch -eq 0 ] && [ $configure -eq 0 ] && [ $build -eq 0 ] && [ $test -eq 0 ]; then
    fetch=1
    configure=1
    build=1
    test=1
fi

H2 " Options "
echo "  command     = ${argv[*]}"
echo "  root        = $root"
echo
echo "  fetch       = $fetch"
echo "  configure   = $configure"
echo "  build       = $build"
echo "  test        = $test"
echo
echo "  fresh       = $fresh"
echo "  append      = $logAppend"
echo
echo "  scriptFilter= $scriptFilter"

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

if [ -n "$1" ]; then
    gitBranch="$1"
    echo "  gitBranch   = $gitBranch"
    shift 1
fi

Fill "- " | Center " Automatic "
platform=$(basename "$(uname -o)")
targetRoot="$root/$target"
echo "  platform    = $platform"
echo "  targetRoot  = $targetRoot"
echo

# Get script count
declare -a buildScripts
buildScripts=($(
    find $targetRoot -maxdepth 1 -type f -name "$platform*" -print \
    | xargs -I '{}' basename '{}' \
    | grep -v "build" \
    | grep -v "actions" \
    | grep -e "$scriptFilter"))

declare -i scriptCount=${#buildScripts[@]}
echo "  Script count: $scriptCount"

#Fail if no scripts
if [ $scriptCount -eq 0 ]; then
    Error "No build scripts found"
    exit 1
fi

# Print Scripts
echo "  Scripts:"
printf "    %s\n" "${buildScripts[@]}"

if [ $list -eq 1 ]; then exit; fi

# Make sure the log directories exist.
mkdir -p "$targetRoot/logs-raw"
mkdir -p "$targetRoot/logs-clean"

# Process Scripts
for script in "${buildScripts[@]}"; do
    # Setup the options each time to clobber any unintended changes.
    declare -a vars
    vars+=("root='$root'")
    vars+=("targetRoot='$targetRoot'")
    vars+=("gitBranch='$gitBranch'")
    vars+=("fetch='$fetch'")
    vars+=("configure='$configure'")
    vars+=("build='$build'")
    vars+=("test='$test'")
    vars+=("fresh='$fresh'")
    vars+=("append='$append'")
    vars+=("verbose='$verbose'")
    vars+=("script='$script'")

    H4 "starting $script"
    config="${script%.*}"

    traceLog="$targetRoot/logs-raw/${config}.txt"
    cleanLog="$targetRoot/logs-clean/${config}.txt"
    echo "    traceLog    = $traceLog"
    echo "    cleanLog    = $cleanLog"

    # set default environment and commands.
    envRun="$SHELL -c"
    envActions="$targetRoot/$platform-actions.sh"
    envClean="CleanLog-Default"
    # source env overrides from script.
    source "$targetRoot/$script" "get_env"

    # Run the action script
    H3 "Start Action"
    $envRun "${vars[*]} . $targetRoot/$envActions" 2>&1 | tee "$traceLog"

    # Cleanup Logs
    $envClean $traceLog > $cleanLog
done
