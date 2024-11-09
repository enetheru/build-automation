#!/usr/bin/env pwsh
#Requires -Version 7.4

[CmdletBinding(PositionalBinding=$false)]
param(
    # [switch] options default to false
    [switch] $freshBuild,
    [switch] $noTestBuild,
    [switch] $appendTrace,

    # Remaining arguments are treated as regex filters for build configs.
    [Parameter(ValueFromRemainingArguments=$true)]$configs
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Make sure we are in the directory of the build script before continuing.
[string]$root = $PSScriptRoot
Set-Location $root
"RootFolder = '$root'"

#Make sure the log paths are available.
New-Item -Path "$root/logs-raw" -ItemType Directory -Force
New-Item -Path "$root/logs-clean" -ItemType Directory -Force

# Source orchestrator common.
. ./orchestrator.ps1

# pull in common functions, and verify config filters against scripts.
. ../build-common.ps1 -prefix "w64" $configs

foreach ($hostTarget in  $buildConfigs) {
    $buildRoot = "$root/$hostTarget"

    SourcePrep -buildRoot $buildRoot -sourceOrigin $sourceOrigin -sourceBranch $sourceBranch

    Prepare -buildRoot $buildRoot

    #separate build command based on prefix.
    w64Build -buildRoot $buildRoot

    Clean -buildRoot $buildRoot -matchPattern '(orchestration.cpp|orchestrator.windows)'

    if( -not $noTestBuild ) {
        Test -buildRoot $buildRoot
    }
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below. The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1
