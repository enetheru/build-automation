#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    [System.Uri]$gitUrl = "http://github.com/godotengine/godot.git"
    if( $gitBranch -eq "" ){ $gitBranch = "master" }
    return
}

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$stats = [PSCustomObject]@{
    fetch   = ($fetch -eq $true) ? "Fail" : "-"
    prepare = ($prepare -eq $true) ? "Fail" : "-"
    build   = ($build -eq $true) ? "Fail" : "-"
    test    = ($test -eq $true) ? "Fail" : "-"
}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    Finalise $stats
    Start-Sleep -Seconds 1
}

. "$root\share\format.ps1"
. "$root\share\build-actions.ps1"

#### Setup our variables

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$targetRoot = $thisScript  | split-path -parent

$config = Split-Path -Path $script -LeafBase

$buildLeaf = ($config -split "-", 2)[-1]

$buildRoot = "$targetRoot\build-$buildleaf"

#### Write Summary ####
SummariseConfig

# Some steps are identical.
function DeleteBuildArtifacts {
    Set-Location "$buildRoot"
    
    [array]$artifacts = @($(rg -u --files "$buildRoot" `
        | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))
    
    if( $artifacts.Length -gt 0 ) {
        H3 "Removing key Artifacts"
        $artifacts | Sort-Object | Get-Unique | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
}

Set-Location "$targetRoot"

# source config-unique action overrides
. "$targetRoot\$script"

H3 "$config - Processing"

if( $fetch      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "Fetch"
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare  -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "Prepare"
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "Build"
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test       -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "Test"
    Test | Tee-Object -Variable result
    ($stats).test = ($result | Select-Object -Last 1)
}

H2 "$config - Completed"

Finalise $stats
Start-Sleep 1
