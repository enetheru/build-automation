# Emscripten SDK location
$emsdk="C:\emsdk"

Set-Location $emsdk
git pull

# perform any updates to emscripten as required.
&"$emsdk\emsdk.ps1" install latest
&"$emsdk\emsdk.ps1" activate latest

Set-Location "$buildRoot/test"
scons verbose=yes platform=web target=template_release

# TODO Run test project
