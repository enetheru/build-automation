#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Error "Do not run this script directly, it simply holds helper functions"
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    H4 "Using Default env Settings"
    return
}

[string]$gitBranch = "4.3"
$emsdk = "C:\emsdk"

function Prepare {
    H1 "Prepare"
    
    # Check Pre-requisites:
    #   - bare git repo
    #   - emscripten SDK
    
    if( -Not (Test-Path -Path "$targetRoot\git" -PathType Container) ) {
        Write-Error "bare git repo is missing."
    }
    
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        Set-Location "$targetRoot\git"
        Format-Eval git worktree add --force "$buildRoot" "$gitBranch"
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    Format-Eval git status
    
    
    H4 "Update EmSDK"
    Set-Location $emsdk
    Format-Eval git pull
    
    # perform any updates to emscripten as required.
    &"$emsdk\emsdk.ps1" install latest
}

function Build {
    H1 "SCons Build"
    $doVerbose = ($verbose -eq $true) ? "verbose=yes" : $null
    
    Set-Location "$buildRoot"
    
    H4 "Activate EmSDK"
    Format-Eval "$emsdk\emsdk.ps1" activate latest
    
    H4 "Build using SCons"
    Format-Eval "scons -j$jobs $doVerbose dlink_enabled=yes target=template_debug"
    Format-Eval "scons -j$jobs $doVerbose dlink_enabled=yes target=template_release"
}
