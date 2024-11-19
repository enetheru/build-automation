# Add the build directory
$buildDir = "$buildRoot\cmake-build"
New-Item -Path $buildDir -ItemType Directory -Force
Set-Location $buildDir

# Build godot-cpp-test
cmake $fresh ../
cmake --build . -j 12 --verbose --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"