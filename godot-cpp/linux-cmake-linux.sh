#!/bin/bash
set -xv
source linux-build_prep.sh

HOST_TARGET=linux-cmake-linux
BUILD_ROOT=$GODOTCPP/$HOST_TARGET

# Clone godot-cpp
# FIXME fatal: destination path '/users/enetheru/build/godot-cpp/linux-cmake-linux' already exists and is not an empty directory.
git clone git@github.com/enetheru/godot-cpp.git $BUILD_ROOT || true
cd $BUILD_ROOT

# Updated to latest for branch
git reset --hard origin
git checkout origin/modernise
git pull

# Compile the test project
mkdir -p cmake-build
cd cmake-build
cmake $FRESH ../ -GNinja
cmake --build . -j 6 --verbose -t godot-cpp-test --config Release

# generate the .godot folder
$GODOT -e --path $BUILD_ROOT/test/project/ --quit --headless &> /dev/null 

# Run the test project
$GODOT_TR --path $BUILD_ROOT/test/project/ --quit --headless
