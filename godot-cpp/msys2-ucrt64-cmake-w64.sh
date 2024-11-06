source msys2_prep.sh

HOST_TARGET=msys2-ucrt64-cmake-w64
BUILD_ROOT=$GODOTCPP/$HOST_TARGET

# Clone godot-cpp
git clone -b modernise /c/Godot/src/godot-cpp $BUILD_ROOT || true
cd $BUILD_ROOT

git reset --hard origin
git pull

# Compile the test project
mkdir -p cmake-build
cd cmake-build
cmake $FRESH ../ && cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# generate the .godot folder
$GODOT -e --path $BUILD_ROOT/test/project/ --quit --headless &> /dev/null 

# Run the test project
$GODOT_TR --path $BUILD_ROOT/test/project/ --quit --headless
