#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

function Prepare {
    Figlet "Prepare"
    
    UpdateAndroid
    
    Set-Location "$buildRoot"
    # TODO Erase key files to trigger a re-build so we can capture the build commands.
    # TODO EraseFiles "basename_pattern" "ext_pattern"
}

function Build {
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    ## SCons Build
    Set-Location "$buildRoot"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    [array]$sconsVars = @(
        "platform=android"
        "arch=x86_64"
    )
    BuildSCons -v $sconsVars -t $targets
    
    # TODO Report Build Artifact sizes
    
    # Report Results
    $statArray | Format-Table
}
