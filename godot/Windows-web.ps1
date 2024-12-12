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

$emsdk = "C:\emsdk"

function Prepare {
    H1 "Prepare"
    
    H4 "Update EmSDK"
    Set-Location $emsdk
    Format-Eval git pull
    
    # perform any updates to emscripten as required.
    &"$emsdk\emsdk.ps1" install latest
}

function Build {
    [array]$statArray = @()
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    
    #SCons build
    $doVerbose = ($verbose -eq $true) ? "verbose=yes" : $null
    $doJobs = ($jobs -gt 0) ? "-j $jobs" : $null
    
    [array]$sconsVars = @(
        "$doVerbose",
        "$doJobs",
        "platform=web",
        "dlink_enabled=yes",
        "threads=no"
    )
    
    Set-Location "$buildRoot"
    
    H4 "Activate EmSDK"
    Format-Eval "$emsdk\emsdk.ps1" activate latest
    
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
