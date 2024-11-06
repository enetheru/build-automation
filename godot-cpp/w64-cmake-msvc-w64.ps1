Set-PSDebug -Trace 1
$hostTarget="w64-cmake-msvc-w64"

# pull in all the common things
. ./w64-build_prep.ps1

# Build godot-cpp-test
cmake $fresh ..\
cmake --build . -j 12 --verbose -t godot-cpp-test --config Release

# Generate the .godot folder
&$godot -e --path "$testProject" --headless --quit *>$null
# Run test project
&$godot_tr --path "$testProject" --headless --quit

Set-PSDebug -Off
