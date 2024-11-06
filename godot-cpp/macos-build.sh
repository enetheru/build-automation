#!/bin/bash
set -xve
# for a fresh configure add FRESH=--fresh to the start of the script invocation
#> FRESH=--fresh ./build.sh

GODOTCPP=$HOME/build/godot-cpp
cd $GODOTCPP

rg -u --files | rg "memory.*o(bj)?" | xargs rm
rg -u --files | rg "example.*o(bj)?" | xargs rm

HOST_TARGET_LIST=(macos-cmake-macos)
for HOST_TARGET in ${HOST_TARGET_LIST[@]}
do
    BUILD_SCRIPT=${GODOTCPP}/${HOST_TARGET}.sh
    TRACE_LOG=${GODOTCPP}/${HOST_TARGET}.txt
    $SHELL -xve $BUILD_SCRIPT 2>&1 | tee $TRACE_LOG
done
