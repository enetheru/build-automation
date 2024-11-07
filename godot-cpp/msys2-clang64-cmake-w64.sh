#!/bin/bash
set -x

GODOT=${GODOT:exit}
GODOT_TR=${GODOT_TR:exit}

echo "$MSYSTEM - $(uname -a)"

# Compile the test project
mkdir -p cmake-build
cd cmake-build || exit

cmake $FRESH ../
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Also skip test if $GODOT and $GODOT_TR are not defined.
if [ "$TEST" -eq 1 ];
then
  # generate the .godot folder
  $GODOT -e --path "$BUILD_ROOT"/test/project/ --quit --headless &> /dev/null

  # Run the test project
  $GODOT_TR --path "$BUILD_ROOT"/test/project/ --quit --headless
fi