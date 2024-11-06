#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    [switch] $freshBuild, # defaults to false
    [switch] $testBuild, # defaults to false
    [switch] $appendTrace # defaults to false
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Main Variables
[string]$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

[string]$root = "C:\build\godot-cpp-template"
[System.Uri]$sourceOrigin = "http://github.com/enetheru/godot-cpp-template.git"
$sourceBranch = "cmake"

# Automtion Begin
Set-Location $root

function TargetPrep {
    param(
        [Parameter(Mandatory=$true)] [string]$hostTarget,
        [Parameter(Mandatory=$true)] [System.Uri]$sourceOrigin,
        $sourceBranch
    )

    Set-Location $root

    [string]$sourceDest = "$root/$hostTarget"

    # Clone the repository
    if( -Not (Test-Path -Path $sourceDest -PathType Container) ){
        git clone (${sourceBranch}?.Insert(0,"-b")) "$sourceOrigin" "$sourceDest"
    }

    # Change working directory
    Set-Location $sourceDest

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if( $sourceBranch ){ git checkout $sourceBranch }

    # Submodules godot-cpp needs its updating to test modernise branch
    if( -Not (Test-Path godot-cpp\*) )
    {
        git submodule set-url -- godot-cpp https://github.com/enetheru/godot-cpp.git
        git submodule set-branch -b modernise godot-cpp
        git submodule sync
        git submodule update --init --recursive --remote
    }

    # Remove key build artifacts before re-build
    # Turn off failure on Non-Zero exit code for ripgrep finding no results
    $PSNativeCommandUseErrorActionPreference = $false
    rg -u --files | rg "\.(lib|dll|a|so|wasm|dylib)$" | ForEach-Object { Remove-Item $_ }
    #Turn back on exit failures.
    $PSNativeCommandUseErrorActionPreference = $true
}

function TargetBuild {
    param(
        $hostTarget,
        $buildRoot
    )
    $buildScript="$root\$hostTarget.ps1"
    $traceLog="$root\$hostTarget.txt"
    $fresh = ($freshBuild) ? "--fresh" : "`$null"

# This script will be source of the exported log, and sources the build script.
@"
#Requires -Version 7.4
Set-StrictMode -Version Latest
`$ErrorActionPreference = "Stop"
`$PSNativeCommandUseErrorActionPreference = `$true

Set-PSDebug -Trace 1

`$godot="$godot"
`$godot_tr="$godot_tr"

`$hostTarget="$hostTarget"
`$buildRoot="$buildRoot"
`$fresh=$fresh

. $buildScript

Set-PSDebug -Off

"@ | pwsh -nop -WorkingDirectory $buildRoot -Command - | Tee-Object -FilePath $traceLog

    # Reset the working directory after we are done.
    Set-Location $root
}


foreach ($hostTarget in  @(
    'w64-scons-msvc-w64'
    'w64-cmake-msvc-w64'
    'w64-cmake-android'
    'w64-cmake-web'
)) {
    TargetPrep -hostTarget $hostTarget -sourceOrigin $sourceOrigin -sourceBranch $sourceBranch
    TargetBuild -hostTarget $hostTarget -buildRoot "$root/$hostTarget"
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below. The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1