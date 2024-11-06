Set-PSDebug -Trace 1
$hostTarget="w64-cmake-web"

# pull in all the common things
. ./w64-build_prep.ps1

$emsdk="C:\emsdk"

# Build godot-cpp-test
&"$emsdk\emsdk.ps1" construct_env
emcmake.bat cmake $fresh ..\
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# TODO Run test project

Set-PSDebug -Off
