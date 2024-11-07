#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    # [switch] options default to false
    [switch] $freshBuild,
    [switch] $noTestBuild,
    [switch] $appendTrace
    # Remaining arguments are treated as targets
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Main Variables
[string]$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

[string]$root = $PSScriptRoot
# [System.Uri]$sourceOrigin = "http://github.com/godotengine/godot-cpp.git"
[System.Uri]$sourceOrigin = "C:\Godot\src\godot-cpp"
[string]$sourceBranch = "modernise"

# Make sure we are in the directory of the build script before continuing.
Set-Location $root

# Process varargs for build configs.
if( $args ){
    $buildConfigs = $args | Where-Object { Test-Path "$_.ps1" }
} else{
    # scan the directory for configs.
    $buildConfigs = (rg --files --max-depth 1 `
        | rg "w64-(cmake|scons).+\.ps1$" ) `
        | ForEach-Object { Split-Path -LeafBase $_ }
}

# Quit if there are no configs.
if( -Not ($buildConfigs -is [array] -And $buildConfigs.count -gt 0) ) {
    if( $args ){ Write-Error "No configs found for: {$args}"
    } else { Write-Error "No Configs found in folder."  }
    exit
}

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

    # Remove key build artifacts before re-build
    # Turn off failure on Non-Zero exit code for ripgrep finding no results
    $PSNativeCommandUseErrorActionPreference = $false
    rg -u --files | rg "\.(lib|dll|a|so|wasm|dylib)$" | ForEach-Object { Remove-Item $_ }
    rg -u --files | rg "(memory|register_types).*?\.(o|obj|so)$" | ForEach-Object { Remove-Item $_ }
    #Turn back on exit failures.
    $PSNativeCommandUseErrorActionPreference = $true
}

function TargetBuild {
    param(
        $hostTarget,
        $buildRoot
    )
    #Script and Log variables
    $buildScript="$root\$hostTarget.ps1"
    $rawLog="$root/logs-raw/$hostTarget.txt"
    $cleanLog="$root/logs-clean/$hostTarget.txt"

    #Build Variables
    $fresh = ($freshBuild) ? "`"--fresh`"" : "`$null"
    $test = ($noTestBuild) ? "`$false" : "`$true"

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
`$test=$test

. $buildScript

Set-PSDebug -Off

"@ | pwsh -nop -WorkingDirectory $buildRoot -Command - | Tee-Object -FilePath $rawLog
    #TODO make the Tee-Object -Append option configurable.

    # Reset the working directory after we are done.
    Set-Location $root

    $matchPattern = '(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern $rawLog | sed -E 's/\s+/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > $cleanLog
}

foreach ($hostTarget in  $buildConfigs) {
    $buildRoot = "$root/$hostTarget"
    TargetPrep -buildRoot $buildRoot -sourceOrigin $sourceOrigin -sourceBranch $sourceBranch
    TargetBuild -hostTarget $hostTarget -buildRoot $buildRoot
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below. The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1