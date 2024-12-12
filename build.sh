#!/bin/bash

set -e          # error and quit when( $? != 0 )
set -u          # error and quit on unbound variable
set -o pipefail # halt when a pipe failure occurs
#set -x          # execute and print

# The root is wherever this script is
platform=$(basename "$(uname -o)")
root=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )

# Source the formatting script
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
   echo "  h, --help        Print this help"
   echo "     --list        Only list the scripts"
   echo
   echo "  f, --fetch       Fetch the source"
   echo "  p, --prepare     prepare the source"
   echo "  b, --build       Build the code"
   echo "  t, --test        Test the code"
   echo
   echo "     --jobs=<int>  How many processors to use"
   echo "     --quiet       Disable verbose"
   echo "     --fresh       Re-Fresh the configuration before building"
   echo "     --append      Append to the log rather than clobber it"
   echo
   echo "     --scriptFilter=<regex> Regex pattern matching script name"
   echo
   exit
}

# Defaults
verbose=1
list=0

if [ "$platform" = "Darwin" ]; then
    jobs=$(( $(sysctl -n hw.ncpu) -1 ))
else
    jobs=$(( $(nproc) -1 ))
fi

fetch=0
prepare=0
build=0
test=0

fresh=0
append=0
scriptFilter=".*"

gitUrl=""
gitBranch=""

# Option parsing pulled from this Stack Overflow Answer from Adam Katz
# https://stackoverflow.com/a/28466267
die() { echo "$*" >&2; exit 2; }  # complain to STDERR and exit with error
needs_arg() { if [ -z "$OPTARG" ]; then Syntax; die "No arg for --$OPT option"; fi; }

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
        p | prepare )   prepare=1 ;;
        b | build )     build=1 ;;
        t | test )      test=1 ;;
        fresh )         fresh=1 ;;
        quiet )         verbose=0 ;;
        append )        append=1 ;;
        jobs )          needs_arg; jobs="$OPTARG" ;;
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

if [ $fetch -eq 0 ] && [ $prepare -eq 0 ] && [ $build -eq 0 ] && [ $test -eq 0 ]; then
    fetch=1
    prepare=1
    build=1
    test=1
fi

H2 " Options "
echo "  command     = ${argv[*]}"
echo "  root        = $root"
echo "  platform    = $platform"
echo
echo "  fetch       = $fetch"
echo "  prepare     = $prepare"
echo "  build       = $build"
echo "  test        = $test"
echo
echo "  jobs        = $jobs"
echo "  fresh       = $fresh"
echo "  append      = $append"
echo
echo "  scriptFilter= $scriptFilter"

# Parse the target
if [ -n "${1:-}" ]; then
    target="$1"
    targetRoot="$root/$target"
    echo "  target      = $target"
    echo "  targetRoot  = $targetRoot"
    shift 1
else
    Syntax
    Error "The <target> parameter is missing"
    exit 1
fi

# Parse the optional branch
if [ -n "${1:-}" ]; then
    gitBranch="$1"
    shift 1
fi

# Get script list
mapfile -t buildScripts < <(
find "$targetRoot" -maxdepth 1 -type f -name "$platform*" -print0 \
    | xargs -0 -I '{}' basename '{}' \
    | grep -v "build" \
    | grep -v "actions" \
    | grep -e "$scriptFilter"
)

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

#Save the vars to an array so we can restore them each loop run.
declare -a savedVars=(
    "verbose='$verbose'"
    "jobs='$jobs'"
    "platform='$platform'"
    "root='$root'"
    "target='$target'"
    "targetRoot='$targetRoot'"
    "gitBranch='$gitBranch'"
    "fetch='$fetch'"
    "prepare='$prepare'"
    "build='$build'"
    "test='$test'"
    "fresh='$fresh'"
    "append='$append'"
)

declare -a summary=(
        "target config status duration fetch prepare build test"
)

# Process Scripts
for script in "${buildScripts[@]}"; do
    #reset variables
    for var in "${savedVars[@]}"; do eval "$var"; done

    H3 "Using '$script'"
    config="${script%.*}"

    traceLog="$targetRoot/logs-raw/${config}.txt"
    cleanLog="$targetRoot/logs-clean/${config}.txt"

    # Reset default environment and commands.
    envRun="$SHELL -c"
    envActions="$platform-actions.sh"
    envClean="CleanLog-Default"

    # source env overrides from script.
    H4 "Source variations from: '$targetRoot/$script'"
    source "$targetRoot/$script" "get_env"

    declare -A stats=(
        ["target"]="$target"
        ["config"]="$config"
        ["status"]="dnf"
        ["duration"]="dnf"
        ["fetch"]=""
        ["prepare"]=""
        ["build"]=""
        ["test"]=""
    )

    declare -a useVars=(
        "verbose='$verbose'"
        "jobs='$jobs'"
        "platform='$platform'"
        "root='$root'"
        "target='$target'"
        "targetRoot='$targetRoot'"
        "gitUrl='$gitUrl'"
        "gitBranch='$gitBranch'"
        "fetch='$fetch'"
        "prepare='$prepare'"
        "build='$build'"
        "test='$test'"
        "fresh='$fresh'"
        "append='$append'"
        "script='$script'"
        "config='$config'"
    )

    # Show action startup details
    if [ $verbose ]; then
        H5 "Command: $envRun"
        H5 "With:"
        printf '\t%s\n' "${useVars[@]}"
        H5 "Action: $targetRoot/$envActions"
        H5 "traceLog: $traceLog"
        H5 "cleanLog: $cleanLog"
    fi

    set +e
    H3 "Start Action"
    declare -i start=$SECONDS
    $envRun "${useVars[*]} $targetRoot/$envActions" 2>&1 | tee "$traceLog"
    stats["duration"]=$((SECONDS - start))
    set -e

    # read the last part of the raw log to collect stats
    mapfile -t data < <(tail -n 20 "$traceLog" | sed -n "/stats\[\"/p")
    for row in "${data[@]}"; do
        eval "$row"
    done

    # Print out the stats in table.
    H3 "$config - Statistics"

    summary+=(
        "$(for col in ${summary[0]}; do
            printf "%s " "${stats[${col}]}"
        done)"
    )

    printf "%s\n%s" "${summary[0]}" "${summary[-1]}" | column -t

    # Cleanup Logs
#    $envClean "$traceLog" > "$cleanLog"
done

H3 Finished
H4 "Original Command: ${argv[*]}"
H3 "Summary"
printf "%s\n" "${summary[@]}" | column -t
