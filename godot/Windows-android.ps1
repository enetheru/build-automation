#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

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
    if( $fresh -eq $true ){
        Remove-Item -Recurse "bin\*"
    }
}

function Build {
    Figlet "Build"
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
