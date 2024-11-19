#!/bin/bash
set -xv
# for a fresh configure add FRESH=--fresh to the start of the script invocation
#> FRESH=--fresh ./build.sh

GODOTCPP=$HOME/build/godot-cpp
cd "$GODOTCPP" || exit

rg -u --files | rg "memory.*o(bj)?" | xargs rm
rg -u --files | rg "example.*o(bj)?" | xargs rm

HOST_TARGET_LIST=(linux-cmake-linux)
for HOST_TARGET in "${HOST_TARGET_LIST[@]}"
do
    BUILD_SCRIPT=${GODOTCPP}/${HOST_TARGET}.sh
    TRACE_LOG=${GODOTCPP}/${HOST_TARGET}.txt
    $SHELL "$BUILD_SCRIPT" 2>&1 | tee "$TRACE_LOG"
done
