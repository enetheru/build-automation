# Run the steps to build
scons verbose=yes target=template_release

#TODO create a varible for testing
if( $false ) {
    # Test afterwards
    $testProject = "$buildRoot\test\project"
    # Generate the .godot folder
    &$godot -e --path "$testProject" --headless --quit *> $null

    # Run test project
    &$godot_tr --path "$testProject" --headless --quit
}