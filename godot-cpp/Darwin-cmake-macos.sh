#!/bin/bash
source macos-build_prep.sh

HOST_TARGET=macos-cmake-macos
BUILD_ROOT=$GODOTCPP/$HOST_TARGET

# Clone godot-cpp
# FIXME fatal: destination path '/users/enetheru/build/godot-cpp/macos-cmake-macos' already exists and is not an empty directory.
git clone -b modernise https://github.com/enetheru/godotcpp.git $BUILD_ROOT || true
cd $BUILD_ROOT

# Updated to latest for branch
git reset --hard
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
