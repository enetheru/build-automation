# Create the build directory
New-Item -Path "cmake-build" -ItemType Directory -Force
Set-Location "cmake-build"

# Run the steps to build
cmake $fresh ..\
cmake --build . --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

#TODO create a varible for testing
if( $false ) {
    # Test afterwards
    $testProject = "$buildRoot\demo"
    # Generate the .godot folder
    &$godot -e --path "$testProject" --headless --quit *> $null

    # Run test project
    &$godot_tr --path "$testProject" --headless --quit
}