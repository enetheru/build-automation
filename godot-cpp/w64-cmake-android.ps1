$toolchain="C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake"
$options="-DANDROID_PLATFORM=android-29 -DANDROID_ABI=x86_64"

# Add the build directory
$buildDir="$buildRoot\cmake-build"
New-Item -Path $buildDir -ItemType Directory -Force
Set-Location $buildDir

# Build godot-cpp-test
cmake $fresh ..\ -GNinja --toolchain $toolchain $options 
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Run test project
