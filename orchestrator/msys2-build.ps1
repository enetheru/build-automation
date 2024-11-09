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

# Make sure we are in the directory of the build script before continuing.
[string]$root = $PSScriptRoot
Set-Location $root

# Source orchestrator common.
. /orchestrator.ps1

. ../build-common.ps1 -prefix "msys2" $args

# Build using msys2
foreach ($msys2Env in @('ucrt64';'mingw64';'mingw32';'clang64';'clang32';'clangarm64') )
{
    $buildScripts=(rg --max-depth 1 --files | rg "msys2-$msys2env.+\.sh$" )
    foreach ($buildScript in $buildScripts)
    {
        $hostTarget = $buildScript | Split-Path -LeafBase
        $buildRoot = "$root/$hostTarget"
        "== Build Configuration : $hostTarget =="
        "BuildRoot: $buildRoot"

        SourcePrep -buildRoot $buildRoot -sourceOrigin $sourceOrigin -sourceBranch $sourceBranch

        Prepare -buildRoot $buildRoot

        msys2Build -msys2Env $msys2Env -hostTarget $hostTarget -buildRoot $buildRoot

        Test -buildRoot $buildRoot
    }
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below. The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1
