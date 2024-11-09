# Add the build directory
$buildDir="$buildRoot\cmake-build"
New-Item -Path $buildDir -ItemType Directory -Force
Set-Location $buildDir

# Build godot-cpp-test
$toolChain="$root\..\toolchains\w64-llvm.cmake"
cmake $fresh ..\ -DCMAKE_BUILD_TYPE:STRING=Release --toolchain $toolChain -GNinja

cmake --build . -j 12 --verbose --config Release