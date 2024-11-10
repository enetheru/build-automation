#!/bin/bash
# Compile the test project

# Check whether this file is sourced or not.
# https://stackoverflow.com/questions/2683279/how-to-detect-if-a-script-is-being-sourced
(return 0 2>/dev/null) && sourced=1 || sourced=0
if [ $sourced -eq 0 ]; then
    echo "Do not run this script directly, it simply holds helper functions"
    exit
fi

Build(){
    figlet SCons

    cd macos-scons/test
    scons verbose=yes target=template_release
}

#Test(){
    figlet Test
    # generate the .godot folder
    #$GODOT -e --path $BUILD_ROOT/test/project/ --quit --headless &> /dev/null 
    
    # Run the test project
    #$GODOT_TR --path $BUILD_ROOT/test/project/ --quit --headless
#}
