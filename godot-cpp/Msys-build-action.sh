#!/bin/bash
set -Ee

COLUMNS=120

godot=${godot:-echo}
godot_tr=${godot_tr:-echo}

gitUrl=http://github.com/enetheru/godot-cpp.git
gitBranch="modernise"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"
cd "$targetRoot"


# Some steps are identical.
CommonPrep(){
    # Clean up key artifacts to trigger rebuild
    rg -u --files "$buildRoot" \
        | rg "(memory|example).*?o(bj)?$" \
        | xargs -r rm
}

CommonTest(){
    H1 "Test" >&5
    # generate the .godot folder
    $godot -e --path "$buildRoot/test/project/" --quit --headless &> /dev/null
    
    # Run the test project
    result=$( \
        $godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
            | tee >(cat >&5) \
        )
    H2 "Test - $config"
    printf '%s' "$result"
    echo "$result" | rg "PASSED" > /dev/null 2>&1
}

# Setup a secondary mechanism for piping to stdout so that we can split output
# of commands to files and show them at the same time.
exec 5>&1

# Process Scripts
cd "$targetRoot"

config=${script%.*}
traceLog=$targetRoot/logs-raw/${config}.txt
cleanLog=$targetRoot/logs-clean/${config}.txt
buildRoot="$targetRoot/$config"

source "$root/build-common.sh"
source "$targetRoot/$script"

{
    H2 "Starting - $config"
    echo "  Build Root = $buildRoot"
    if ! Fetch;   then echo "${RED}Error: Fetch Failure${NC}"  ; exit 1; fi
    if ! Prepare; then echo "${RED}Error: Prepare Failure${NC}"; exit 1; fi
    if ! Build;   then echo "${RED}Error: Build Failure${NC}"  ; exit 1; fi
    if ! Test >> "$targetRoot/summary.log"; then
        echo "${RED}Error: Test Failure${NC}"; fi
    if ! Clean;   then echo "${RED}Error: Clean Failure${NC}"  ; fi
} 2>&1 | tee "$traceLog"

matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' \
    | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"
