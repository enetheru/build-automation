
Set-Location "$buildRoot/test"
scons verbose=yes target=template_release

if( -Not $test ) {
    # Generate the .godot folder
    &$godot -e --path "$buildRoot/test/Project" --headless --quit *> $null
    # Run test project
    &$godot_tr --path "$buildRoot/test/Project" --headless --quit
}
