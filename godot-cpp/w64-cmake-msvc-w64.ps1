# Add the build directory
$buildDir="$buildRoot\cmake-build"
New-Item -Path $buildDir -ItemType Directory -Force
Set-Location $buildDir

# Build godot-cpp-test
cmake $fresh ..\
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

if( -Not $test ) {
    # Generate the .godot folder
    &$godot -e --path "$buildRoot/test/Project" --headless --quit *> $null
    # Run test project
    &$godot_tr --path "$buildRoot/test/Project" --headless --quit
}