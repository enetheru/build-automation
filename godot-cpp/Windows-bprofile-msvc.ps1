#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c) {
    $gitHash = "build_profile"
    return
}

function Prepare {
    Figlet "Prepare"
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "example|editor_plugin_registration" "o|obj|os"
    EraseFiles "libgodot-cpp.windows" "a"
    EraseFiles "libgdexample.windows" "dll"
    
    $cmakeVars = @(
        "-DGODOT_ENABLE_TESTING=YES"
        "-DGODOT_BUILD_PROFILE='..\test\build_profile.json'"
    )
    PrepareCMake -v $cmakeVars
}

function Build {
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles "libgdexample" "dll"
    EraseFiles "libgodot-cpp" "lib"
    
    ## SCons Build
    Set-Location "$buildRoot\test"
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    $sconsVars = @("build_profile=build_profile.json")
    BuildSCons -t $targets -v $sconsVars
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles "libgdexample" "dll"
    EraseFiles "libgodot-cpp" "lib"
    
    ## CMake Build
    Set-Location "$buildRoot\cmake-build"
    
    [array]$msbuildOpts = @(
        "/nologo",
        "/v:m",
        "/clp:'ShowCommandLine;ForceNoAlign'"
    )
    [array]$targets = @(
        "godot-cpp.test.template_debug",
        "godot-cpp.test.template_release",
        "godot-cpp.test.editor")
    BuildCMake -v @("--config Release") -t $targets -e $msbuildOpts
    
    # Report Results
    $statArray | Format-Table
}
