#!/bin/bash
set -Ee
prev_dir=$(pwd)

gitUrl=http://github.com/enetheru/godot-cpp.git
gitBranch="modernise"

echo 
echo " == Build $target using Darwin =="
thisScript="$(basename $0)"
echo "  thisScript  = $thisScript"

# Get the target root from this script location
targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"
cd $targetRoot

# Set pattern variable from first argument
if [ -n "$argv[1]" ]; then
    pattern="$argv[1]"
    echo "  pattern     = $pattern"
fi

# Get script count
buildScripts=($(rg -u --files --max-depth 1 | \
    rg "Darwin.*sh" | \
    rg -v "$thisScript"))

echo "  Script count: ${#buildScripts}"

#Fail if no scripts
if [ ${#buildScripts} -eq 0 ]; then
    echo
    echo "  ${RED}Error: No build scripts found${NC}"
    cd $prev_dir
    exit 1
fi

# Print Scripts
echo "  Scripts:"
for script in $buildScripts; do
    echo "    $script"
done

# Make sure the log directories exist.
mkdir -p $targetRoot/logs-raw
mkdir -p $targetRoot/logs-clean


# Some steps are identical.
CommonPrep(){
    # Clean up key artifacts to trigger rebuild
    rg -u --files $buildRoot \
        | rg "(memory|example).*?o(bj)?$" \
        | xargs rm
    CustomPrep
}

CommonTest(){
    # generate the .godot folder
    $godot -e --path $buildRoot/test/project/ --quit --headless &> /dev/null 
    
    # Run the test project
    $godot_tr --path $buildRoot/test/project/ --quit --headless
}

# Process Scripts
for script in $buildScripts; do
    cd $targetRoot

    config=${script%.*}
    traceLog=$targetRoot/logs-raw/${config}.txt
    cleanLog=$targetRoot/logs-clean/${config}.txt
    buildRoot="$targetRoot/$config"

    source $root/build-common.sh
    source $targetRoot/$script
    RenameFunction Prepare CustomPrep
    RenameFunction CommonPrep Prepare
    RenameFunction CommonTest Test

    {
        echo
        echo " == Starting $(basename $script) =="
        echo "  Build Root = $buildRoot"
        if ! Fetch;   then echo "${RED}Error: Fetch Failure${NC}"  ; continue; fi
        if ! Prepare; then echo "${RED}Error: Prepare Failure${NC}"; continue; fi
        if ! Build;   then echo "${RED}Error: Build Failure${NC}"  ; continue; fi
        if ! Test;    then echo "${RED}Error: Test Failure${NC}"   ; fi
        if ! Clean;   then echo "${RED}Error: Clean Failure${NC}"  ; fi
    } 2>&1 | tee $traceLog

    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern $traceLog | sed -E 's/ +/\n/g' \
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > $cleanLog
done

cd $prev_dir
