# Create the build directory
New-Item -Path "cmake-build" -ItemType Directory -Force
Set-Location "cmake-build"

# Build godot-cpp-test
$emsdk = "C:\emsdk"
&"$emsdk\emsdk.ps1" construct_env
emcmake.bat cmake $fresh ..\
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

#TODO create a varible for testing
if( $false ) {
    # TODO Test
    #    $testProject = "$buildRoot\demo"
    # TODO Generate .godot folder
    # TODO run project
}