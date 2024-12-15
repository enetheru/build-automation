#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    H4 "Using Default env Settings"
    return
}

function Prepare {
    Figlet "Prepare"
    
    UpdateAndroid
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|obj"
    
    PrepareScons -v @("platform=android")
    
    [array]$cmakeVars = @(
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGODOT_ENABLE_TESTING=YES",
        "-DANDROID_PLATFORM=android-34",
        "-DANDROID_ABI=x86_64",
        "--toolchain `"C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake`""
    )
    
    PrepareCMake -v $cmakeVars
}

function Build {
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
#    EraseFiles -f "libgdexample" -e "dll" # FIXME update for android
    
    # SCons Build
    Set-Location "$buildRoot\test"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    [array]$sconsVars = @(
        "platform=android"
        "arch=x86_64"
    )
    BuildSCons -v $sconsVars -t $targets
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    #    EraseFiles -f "libgdexample" -e "dll" # FIXME update for android
    
    ## CMake Build
    Set-Location "$buildRoot\cmake-build"
    [array]$targets = @(
        "godot-cpp.test.template_debug",
        "godot-cpp.test.template_release",
        "godot-cpp.test.editor")
    BuildCMake -t $targets
    
    # Report Results
    $statArray | Format-Table
}