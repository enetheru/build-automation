#!/bin/bash
# set -xve
# for a fresh configure add FRESH=--fresh to the start of the script invocation
#> FRESH=--fresh ./build.sh

if [ "$(which -s rg)" = "rg not found" ]; then
    echo "${RED}Error: Unable to find Ripgrep${NC}"
    exit 1
fi

prev_dir=$(pwd)

echo 
echo " == Build $target using Darwin =="
thisScript="$(basename $0)"
echo "basename: $thisScript"
target_dir=$( cd -- "$( dirname -- "$0}" )" &> /dev/null && pwd )
echo "target_dir: $target_dir"

if [ -n "$argv[1]" ]; then
    pattern="$argv[1]"
    echo "pattern=$pattern"
fi

cd $target_dir

buildScripts=$(rg -u --files --max-depth 1 | rg "Darwin.*sh" | rg -v "$thisScript")
echo $buildScripts

for buildScript in $buildScripts; do
    echo $buildScript
    Source
    prepare
    Build
    Clean
done

cd $prev_dir
exit

rg -u --files | rg "memory.*o(bj)?" | xargs rm
rg -u --files | rg "example.*o(bj)?" | xargs rm

HOST_TARGET_LIST=(macos-cmake-macos)
for HOST_TARGET in ${HOST_TARGET_LIST[@]}
do
    BUILD_SCRIPT=${GODOTCPP}/${HOST_TARGET}.sh
    TRACE_LOG=${GODOTCPP}/${HOST_TARGET}.txt
    $SHELL -xve $BUILD_SCRIPT 2>&1 | tee $TRACE_LOG
done
