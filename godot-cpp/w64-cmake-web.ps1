# Perform any updates to emscripten as required.
$emsdk="C:\emsdk"
Set-Location $emsdk
git pull
&"$emsdk\emsdk.ps1" install latest
&"$emsdk\emsdk.ps1" activate latest

# Add the build directory
$buildDir="$buildRoot\cmake-build"
New-Item -Path $buildDir -ItemType Directory -Force
Set-Location $buildDir

#build using cmake
emcmake.bat cmake $fresh ..\
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Run test project
