#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
#    [System.Uri]$gitUrl = "http://github.com/godotengine/godot.git"
    [System.Uri]$gitUrl = "C:\Godot\src\godot"
    if( $gitBranch -eq "" ){ $gitBranch = "master" }
    return
}

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

. "$root\share\format.ps1"
. "$root\share\build-actions.ps1"

$stats = [PSCustomObject]@{}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    Finalise $stats
    Start-Sleep -Seconds 1
}

#### Setup our variables

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$targetRoot = $thisScript  | split-path -parent

$config = Split-Path -Path $script -LeafBase

$buildRoot = "$targetRoot\$config"


#### Write Summary ####
SummariseConfig

Set-Location "$targetRoot"

# Per config Overrides and functions
. "$targetRoot\$script"

H3 "$config - Processing"

DefaultProcess

H2 "$config - Completed"

Finalise $stats
Start-Sleep 1
