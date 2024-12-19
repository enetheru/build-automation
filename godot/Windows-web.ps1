#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

$script:emsdk = "C:\emsdk"

function Prepare {
    Figlet "Prepare"
    
    UpdateEmscripten
    
    Set-Location "$buildRoot"
    # TODO Erase key files to trigger a re-build so we can capture the build commands.
    # TODO EraseFiles "basename_pattern" "ext_pattern"
}

function Build {
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    H4 "Activate EmSDK"
    Format-Eval "$emsdk\emsdk.ps1" activate latest
    
    ## SCons Build
    Set-Location "$buildRoot"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    [array]$sconsVars = @(
        "platform=web",
        "dlink_enabled=yes",
        "threads=no")
    BuildSCons -v $sconsVars -t $targets
    
    # TODO Report Build Artifact sizes
    
    # Report Results
    $statArray | Format-Table
}
