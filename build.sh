#!/bin/bash


#########################    Setup Bash Preferences   #########################
set -e          # error and quit when( $? != 0 )
set -u          # error and quit on unbound variable
set -o pipefail # halt when a pipe failure occurs
#set -x          # execute and print

root=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )

#### Source Text Formatting Functions
source "$root/share/aarray.sh"
source "$root/share/format.sh"

##########################    Function Definitions    #########################
Syntax()
{
   echo "Syntax: ./build.sh [-hfcbt] [--list] [--fresh] [--append] [--filter=<regex>] <target> [gitBranch]"
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
   echo "     --filter=<regex> Regex pattern matching script name"
   echo
   exit
}
if echo "${@}" | grep -qEe "--help|-h"; then Help; fi

########################    Process Parameter Flags    ########################
# Option parsing pulled from this Stack Overflow Answer from Adam Katz
# https://stackoverflow.com/a/28466267
die() { echo "$*" >&2; exit 2; }  # complain to STDERR and exit with error
needs_arg() { if [ -z "$OPTARG" ]; then Syntax; die "No arg for --$OPT option"; fi; }

while getopts :hfpbt-: OPT; do  # allow -a, -b with arg, -c, and -- "with arg"
    # support long options: https://stackoverflow.com/a/28466267/519360
    if [ "$OPT" = "-" ]; then   # long option: reformulate OPT and OPTARG
        OPT="${OPTARG%%=*}"       # extract long option name
        OPTARG="${OPTARG#"$OPT"}" # extract long option argument (may be empty)
        OPTARG="${OPTARG#=}"      # if long option argument, remove assigning `=`
    fi
    # shellcheck disable=SC2034
    case "$OPT" in
        h | help )      Help ;;
        quiet )         verbose=0 ;;
        list )          list=1 ;;
        jobs )          needs_arg; jobs="$OPTARG" ;;
        f | fetch )     fetch=1 ;;
        p | prepare )   prepare=1 ;;
        b | build )     build=1 ;;
        t | test )      test=1 ;;
        fresh )         fresh=1 ;;
        append )        append=1 ;;
        filter )  needs_arg; filter="$OPTARG" ;;
        # c | charlie )  charlie="${OPTARG:-$charlie_default}" ;;  # optional argument
        \? )           echo "Error: Bad short option" >&2; Syntax; exit 2 ;;  # bad short option (error reported via getopts)
        * )            die "Illegal option --$OPT" ;;            # bad long option
    esac
done
shift $((OPTIND-1)) # remove parsed options and args from $@ list

# Default and Detected Settings
platform=$(basename "$(uname -o)")


verbose=${verbose:-1}
list=${list:-0}

if [ "$platform" = "Darwin" ];
then nproc=$(( $(sysctl -n hw.ncpu) -1 ))
else nproc=$(( $(nproc) -1 ))
fi
jobs=${jobs:-$((nproc -1))}

fetch=${fetch:-0}
prepare=${prepare:-0}
build=${build:-0}
test=${test:-0}

fresh=${fresh:-0}
append=${append:-0}
filter=${filter:-".*"}

gitUrl=""
gitBranch=""

argv[0]="$0"
argv+=("${@}")

if [ $fetch -eq 0 ] && [ $prepare -eq 0 ] && [ $build -eq 0 ] && [ $test -eq 0 ]; then
    fetch=1
    prepare=1
    build=1
    test=1
fi

# Parse the target
if [ -n "${1:-}" ]; then
    target="$1"
    targetRoot="$root/$target"
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


#### Source Configuration and Function Overrides from Target Actions
source "$targetRoot/$platform-actions.sh" "get_config"

#############################    Print Summary    #############################
H1 "AutoBuild"
H2 "Options"

echo "
  platform    = $platform
  root        = $root
  command     = $0

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test

  jobs        = $jobs

  fresh       = $fresh
  append      = $append

  target      = $target
  targetRoot  = $targetRoot

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch
"

# Get Target Scripts
# On Macos bash is version 3.2, which means mapfile isn't available and the
# below won't work. 
# mapfile -t buildScripts < <( ... )
#
# So this stack overflow answer describes how to use read -r
# https://stackoverflow.com/a/41475317
declare -a buildScripts=()
while IFS= read -r line; do
    buildScripts+=("$line")
done < <(
find "$targetRoot" -maxdepth 1 -type f -name "$platform*" -print0 \
    | xargs -0 -I '{}' basename '{}' \
    | grep -v "build" \
    | grep -v "actions" \
    | grep -e "$filter"
)
# Get the script count
declare -i scriptCount=${#buildScripts[@]}

echo "
  filter= $filter
  scriptCount = $scriptCount
"

#Fail if no scripts
if [ $scriptCount -eq 0 ]; then
    Error "No build scripts found"
    exit 1
fi

# Print Scripts
echo "  Scripts:"
printf "    %s\n" "${buildScripts[@]}"

if [ "$list" -eq 1 ]; then exit; fi



############################    Save Variables    #############################
#Save the vars to an array so we can restore them each loop run.
declare -a savedVars=(
    "verbose='$verbose'"
    "jobs='$jobs'"

    "fetch='$fetch'"
    "prepare='$prepare'"
    "build='$build'"
    "test='$test'"

    "fresh='$fresh'"
    "append='$append'"

    "platform='$platform'"
    "target='$target'"

    "root='$root'"
    "targetRoot='$targetRoot'"

    "gitUrl='$gitUrl'"
    "gitBranch='$gitBranch'"
)

############################    Begin Processing    ###########################
#                                                                             #
#           ██████  ██████   ██████   ██████ ███████ ███████ ███████          #
#           ██   ██ ██   ██ ██    ██ ██      ██      ██      ██               #
#           ██████  ██████  ██    ██ ██      █████   ███████ ███████          #
#           ██      ██   ██ ██    ██ ██      ██           ██      ██          #
#           ██      ██   ██  ██████   ██████ ███████ ███████ ███████          #

# Make sure the log directories exist.
mkdir -p "$targetRoot/logs-raw"
mkdir -p "$targetRoot/logs-clean"


## Clone to bare repo or update
#H3 "Git Update/Clone Bare Repository"
#if [ ! -d "$targetRoot/git" ]; then
#    Format-Eval "git clone --bare \"$gitUrl\" \"$targetRoot/git\""
#else
#    Format-Eval "git --git-dir=\"$targetRoot/git\" fetch --force origin *:*"
#    Format-Eval "git --git-dir=\"$targetRoot/git\" worktree prune"
#    Format-Eval "git --git-dir=\"$targetRoot/git\" worktree list"
#fi

declare -a summary=(
        "config fetch prepare build test status duration"
)

# Process Scripts
for script in "${buildScripts[@]}"; do
    H3 "Processing '$script'"

    #reset variables
    for var in "${savedVars[@]}"; do eval "$var"; done

    config="${script%.*}"
    buildRoot="$targetRoot/$config"

    traceLog="$targetRoot/logs-raw/${config}.txt"
    cleanLog="$targetRoot/logs-clean/${config}.txt"

    # Reset default environment and commands.
    envRun="$SHELL -c"
    envActions="$platform-actions.sh"
    envClean="CleanLog-Default"

    # source env overrides from script.
    H4 "Source variations from: '$targetRoot/$script'"
    source "$targetRoot/$script" "get_env"

    declare -a useVars=(
        "verbose='$verbose'"
        "jobs='$jobs'"

        "platform='$platform'"
        "root='$root'"
        "target='$target'"

        "targetRoot='$targetRoot'"

        "script='$script'"
        "config='$config'"

        "buildRoot='$buildRoot'"

        "fetch='$fetch'"
        "prepare='$prepare'"
        "build='$build'"
        "test='$test'"

        "fresh='$fresh'"
        "append='$append'"

        "gitUrl='$gitUrl'"
        "gitBranch='$gitBranch'"

        "traceLog='$traceLog'"
        "cleanLog='$cleanLog'"
    )

    # Show action startup details
    if [ $verbose ]; then
        H5 "Command: $envRun"
        H5 "With:"
        printf '\t%s\n' "${useVars[@]}"
        H5 "Action: $targetRoot/$envActions"
    fi

    # Bash 3.2 does not have associative arrays, so I am going to have
    # to work around that.
    declare -a stats=(
        "config:$config"
        "fetch:-"
        "prepare:-"
        "build:-"
        "test:-"
        "status:dnf"
        "duration:dnf"
    )

    set +e
    declare -i start=$SECONDS

    $envRun "${useVars[*]} $targetRoot/$envActions" 2>&1 | tee "$traceLog"

    if [ $? ]; then AArrayUpdate stats status Completed; fi
    AArrayUpdate stats duration $((SECONDS - start))
    set -e

    # read the last part of the raw log to collect stats
    # Another location where we cannot use 'mapfile -t'
    # mapfile -t data < <(tail -n 20 "$traceLog" | sed -n "/stats\[\"/p")
    # for row in "${data[@]}"; do eval "$row"; done
    while IFS= read -r line; do
        $line
    done < <( tail -n 20 "$traceLog" | sed -n "/AArrayUpdate/p" )

    summary+=(
        "$(for col in ${summary[0]}; do
            printf "%s " "$(AArrayGet stats $col)"
        done)"
    )

    # Print out the stats in table.
    H3 "$config - Statistics"
    printf "%s\n%s" "${summary[0]}" "${summary[-1]}" | column -t

    # Cleanup Logs
    H3 "Process Logs"
    CleanLog "$traceLog" > "$cleanLog"
done

H1 "Finished"
H3 "Original Command: ${argv[*]}"

if [ "${#buildScripts[@]}" -gt 1 ]; then
    H3 "Summary"
    printf "%s\n" "${summary[@]}" | column -t -R 6
fi
