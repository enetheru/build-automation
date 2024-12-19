#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

$script:emsdk = "C:\emsdk"

function FetchOverride {
    Figlet "Fetch"
    
    UpdateAndroid
    
    # https://stackoverflow.com/questions/24347758/remove-alias-in-script
    Remove-Item 'Alias:\Fetch' -Force
    Fetch #Original Fetch
}
New-Alias -Name 'Fetch' -Value 'FetchOVerride' -Scope Global

function Prepare {
    Figlet "Prepare"
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|d|obj"
    EraseFiles "libgodot-cpp.android" "a"
    
    PrepareScons -v @("platform=android")
    
    [array]$cmakeVars = @(
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGODOT_ENABLE_TESTING=YES",
        "-DANDROID_PLATFORM=latest",
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