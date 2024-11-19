## macos-scons

```bash
# Clone godot-cpp
cd ~/build/godot-cpp
git clone http://github.com/godotengine/godot-cpp.git macos-scons

# build godot-cpp-test
cd macos-scons/test
scons verbose=yes target=template_release

# Run tests
GODOT=~/build/godot/macos-master/bin/godot.macos.editor.arm64
$GODOT -e --path project/ --headless --quit > /dev/null
GODOT_TR=~/build/godot/macos-master-tr/bin/godot.macos.template_release.arm64
$GODOT_TR --path project --headless --quit
```

## macos-cmake

```bash
# Clone godot-cpp
cd ~/build/godot-cpp
git clone http://github.com/enetheru/godot-cpp.git macos-cmake
cd macos-cmake
git checkout enetheru/modernise

# build godot-cpp-test
mkdir cmake-build
cd cmake-build
cmake ../ -GNinja && cmake --build . --verbose -t godot-cpp-test --config Release

# FAILED
```

Crap I haven't been documenting my changes.

So I installed emscripten, and android I'll have to get back with the exact
package names.

brew install emscripten android-commandlinetools

android requested I install java

brew install --cask temurin

for the web build this appears to have been enough.

Running a build for the godot-cpp with `scons platform=web` seems to be going
ok.

I have to check the emscripten notes if I want to run it with cmake it's
spitting a permission denied error:

```text
/o/opt/homebrew/opt/emscripten/bin/emcmake ../
configure: ../ \ 
    -DCMAKE_TOOLCHAIN_FILE=/opt/homebrew/Cellar/emscripten/3.1.70/libexec/cmake/Modules/Platform/Emscripten.cmake \
    -DCMAKE_CROSSCOMPILING_EMULATOR=/opt/homebrew/opt/node/bin/node
emcmake: error: '../
    -DCMAKE_TOOLCHAIN_FILE=/opt/homebrew/Cellar/emscripten/3.1.70/libexec/cmake/Modules/Platform/Emscripten.cmake \
    -DCMAKE_CROSSCOMPILING_EMULATOR=/opt/homebrew/opt/node/bin/node'
    failed: [Errno 13] Permission denied: '../'
```

https://emscripten.org/docs/getting_started/downloads.html#platform-notes-installation-instructions-sdk

OK it's because cmake needs to be the first argument for emcmake.

Interestingly it spat this error:

```text
configure: cmake ../ -GNinja 
  -DCMAKE_TOOLCHAIN_FILE=/opt/homebrew/Cellar/emscripten/3.1.70/libexec/cmake/Modules/Platform/Emscripten.cmake
  -DCMAKE_CROSSCOMPILING_EMULATOR=/opt/homebrew/opt/node/bin/node
Auto-detected 8 CPU cores available for build parallelism.

CMake Warning (dev) at test/CMakeLists.txt:4 (add_library):
  ADD_LIBRARY called with SHARED option but the target platform does not
  support dynamic linking.  Building a STATIC library instead.  This may lead
  to problems.
This warning is for project developers.  Use -Wno-dev to suppress it.
```

https://github.com/emscripten-core/emscripten/issues/20340

discussion bout why it's disabled.

## IOS

https://github.com/leetal/ios-cmake

## emscripten

I did install emscripten from brew, but uninstalled it and preferred to follow
the instructions from the emscripten website.

now it wants me to source the env.

`source ~/emsdk/emsdk_env.sh`


