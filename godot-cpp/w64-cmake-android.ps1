Set-PSDebug -Trace 1
$hostTarget="w64-cmake-android"

# pull in all the common things
. ./w64-build_prep.ps1

$toolchain="C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake"
$options="-DANDROID_PLATFORM=android-29 -DANDROID_ABI=x86_64"

# Build godot-cpp-test
cmake $fresh ..\ -GNinja --toolchain $toolchain $options 
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Run test project

Set-PSDebug -Off
