#!/bin/bash
set -x
echo "$MSYSTEM - $(uname -a)"

cd $BUILD_ROOT/test
scons verbose=yes target=template_release use_mingw=yes use_llvm=yes

# TODO Also skip test if $GODOT and $GODOT_TR are not defined.
if [ "$TEST" -eq 1 ];
then
  # generate the .godot folder
  $GODOT -e --path "$BUILD_ROOT/test/project" --quit --headless &> /dev/null

  # Run the test project
  $GODOT_TR --path "$BUILD_ROOT/test/project" --quit --headless
fi