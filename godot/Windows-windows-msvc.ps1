#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c -eq $true ) {
    H4 "Using Default env Settings"
    return
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
    
    Set-Location "$buildRoot"
    
    foreach( $target in $targets ) {
        H2 "$target"; H1 "SCons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "scons $doJobs $doVerbose target=$target"
        
        H4 "$target duration: $($timer.Stop();$timer.Elapsed)"
        
        $artifact = Get-ChildItem "$buildRoot\bin\godot.windows.$target.x86_64.exe"
        $statArray += [PSCustomObject] @{
            target      = "scons.$target"
            duration    = $timer.Elapsed
            size        = DisplayInBytes $artifact.Length
        }
    }
    
    $statArray | Format-Table
}
