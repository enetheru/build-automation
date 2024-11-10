#!/bin/bash
set -Ee
# for a fresh configure add FRESH=--fresh to the start of the script invocation
#> FRESH=--fresh ./build.sh

gitUrl=http://github.com/enetheru/godot-cpp.git
gitBranch="modernise"

prev_dir=$(pwd)

echo 
echo " == Build $target using Darwin =="
thisScript="$(basename $0)"
echo "  thisScript  = $thisScript"
targetRoot=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "  targetRoot  = $targetRoot"

if [ -n "$argv[1]" ]; then
    pattern="$argv[1]"
    echo "  pattern     = $pattern"
fi

cd $targetRoot

buildScripts=($(rg -u --files --max-depth 1 | \
    rg "Darwin.*sh" | \
    rg -v "$thisScript"))

echo "  Script count: ${#buildScripts}"
if [ ${#buildScripts} -eq 0 ]; then
    echo
    echo "  ${RED}Error: No build scripts found${NC}"
    cd $prev_dir
    exit 1
fi

echo "  Scripts:"
for script in $buildScripts; do
    echo "    $script"
done

for script in $buildScripts; do
    config=${script%.*}
    traceLog=$targetRoot/logs-raw/${config}.txt
    cleanLog=$targetRoot/logs-clean/${config}.txt
    cd $targetRoot
    source $root/build-common.sh
    source $targetRoot/$script
    {
        echo
        echo " == Starting $(basename $script) =="
        buildRoot="$targetRoot/$config"
        echo "  Build Root = $buildRoot"

        if ! Fetch;   then echo "${RED}Error: Fetch Failure${NC}"  ; continue; fi
        if ! Prepare; then echo "${RED}Error: Prepare Failure${NC}"; continue; fi
        if ! Build;   then echo "${RED}Error: Build Failure${NC}"  ; continue; fi
        if ! Test;    then echo "${RED}Error: Test Failure${NC}"   ; fi
        if ! Clean;   then echo "${RED}Error: Clean Failure${NC}"  ; fi
    } 2&>1 | tee $traceLog

    matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern $traceLog | sed -E 's/\s+/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > $cleanLog
done

cd $prev_dir

# rg -u --files | rg "memory.*o(bj)?" | xargs rm
# rg -u --files | rg "example.*o(bj)?" | xargs rm
# 
# HOST_TARGET_LIST=(macos-cmake-macos)
# for HOST_TARGET in ${HOST_TARGET_LIST[@]}
# do
#     BUILD_SCRIPT=${GODOTCPP}/${HOST_TARGET}.sh
#     TRACE_LOG=${GODOTCPP}/${HOST_TARGET}.txt
#     $SHELL -xve $BUILD_SCRIPT 2>&1 | tee $TRACE_LOG
# done
