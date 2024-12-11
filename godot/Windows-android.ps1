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

$androidSDK = "C:\androidsdk\cmdline-tools\latest\bin"

function Prepare {
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null
    H1 "Prepare"
    
    H3 "Add Android SDK Manager to PATH"
    $env:Path = "$androidSDK;" + $env:Path
    
    sdkmanager --update $doVerbose
}

function Build {
    $doVerbose = ($verbose -eq $true) ? "verbose=yes" : $null
    $doJobs = ($jobs -gt 0) ? "-j $jobs" : $null
    
    [array]$statArray = @()
    
    $targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    
    [array]$sconsVars = @(
        "platform=android"
        "arch=x86_64"
    )
    
    Set-Location "$buildRoot"
    
    foreach( $target in $targets ) {
        H2 "$target"; H1 "SCons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "scons $doJobs $doVerbose target=$target $($sconsVars -Join ' ')"
        
        $timer.Stop()
        
#        $artifact = Get-ChildItem "$buildRoot\bin\godot.web.$target.x86_64.wasm"
        $newStat = [PSCustomObject] @{
            target      = "scons.$target"
            duration    = $timer.Elapsed
#            size        = DisplayInBytes $artifact.Length
        }
        $newStat | Format-Table
        $statArray += $newStat
    }
    
    $statArray | Format-Table
}
