# Create the build directory
New-Item -Path "cmake-build" -ItemType Directory -Force
Set-Location "cmake-build"

#Toolchain
$toolchain="C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake"
$options="-DANDROID_PLATFORM=android-29 -DANDROID_ABI=x86_64"

# Build godot-cpp-test
cmake $fresh ..\ -GNinja --toolchain $toolchain $options
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

if( $false ) #TODO create a varible for testing
{
    # TODO Test
#    $testProject = "$buildRoot\demo"
    # TODO Generate .godot folder
    # TODO run project
}