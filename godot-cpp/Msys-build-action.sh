#!/bin/bash
set -Ee

declare -i columns=120

gitUrl=http://github.com/enetheru/godot-cpp.git
gitBranch="modernise"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"
cd "$targetRoot"


# Some steps are identical.
CommonPrep(){
    local prev=$(pwd)
    cd "$buildRoot" || exit 1
    # Clean up key artifacts to trigger rebuild
    declare -a artifacts
    artifacts+=($(rg -u --files \
        | rg "(memory|example).*?o(bj)?$"))
    artifacts+=($(rg -u --files \
        | rg "\.(a|lib|so|dll|dylib)$"))

    if [ -n "${artifacts[*]}" ]; then
      H3 "Prepare"
      Warning "Deleting key Artifacts"
      for item in "${artifacts[@]}"; do
        echo "rm '$item'"
        rm "$item"
      done
    fi
    cd "$prev"
}

CommonTest(){
    H1 "Test" >&5

    local godot=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe
    local godot_tr=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe

    # generate the .godot folder
    $godot -e --path "$buildRoot/test/project/" --quit --headless &> /dev/null
    
    # Run the test project
    local result
    result=$( $godot_tr --path "$buildRoot/test/project/" --quit --headless 2>&1 \
            | tee >(cat >&5) )
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
