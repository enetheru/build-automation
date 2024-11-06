#!/bin/bash
set -xv

echo "$MSYSTEM - $(uname -a)"

echo "godot=$GODOT"
echo "godot_tr=$GODOT_TR"

echo "fresh=$FRESH"
echo "test=$TEST"

## Compile the test project
mkdir -p cmake-build
cd cmake-build || exit

cmake "$FRESH" ../
cmake --build . -j 12 --verbose --config Release

if [ "$TEST" -eq 1 ];
then
  # generate the .godot folder
  $GODOT -e --path "${BUILD_ROOT}/demo" --quit --headless &> /dev/null

  # Run the test project
  $GODOT_TR --path "${BUILD_ROOT}/demo" --quit --headless
fi


