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

[string]$root = $PSScriptRoot
#[System.Uri]$sourceOrigin = "http://github.com/enetheru/godot-cpp.git"
[System.Uri]$sourceOrigin = "C:/Godot/src/godot-cpp"
[string]$sourceBranch = "4.3-modernise"

# Make sure we are in the directory of the build script before continuing.
Set-Location $root

. ../build-common.ps1 -prefix "msys2" $args

function LocalPrep {
    param(
        [Parameter(Mandatory=$true)] [string]$buildRoot
    )

    Set-Location $buildRoot

    # Remove key build artifacts before re-build
    # Turn off failure on Non-Zero exit code for ripgrep finding no results
    $PSNativeCommandUseErrorActionPreference = $false
    rg -u --files | rg "\.(dll|so|wasm|dylib|lib)$" | ForEach-Object { Remove-Item $_ }
    rg -u --files | rg "register_types.*?\.(o|obj|so)$" | ForEach-Object { Remove-Item $_ }
    #Turn back on exit failures.
    $PSNativeCommandUseErrorActionPreference = $true
}

function TargetBuild {
    param(
        [Parameter(Mandatory=$true)] [string]$buildRoot,
        $msys2Env,
        $hostTarget
    )
    # Script and log variables
    $msys2_shell="C:/msys64/msys2_shell.cmd -$msys2Env -defterm -no-start -where $buildRoot"
    $rawLog="$root/logs-raw/$hostTarget.txt"
    $cleanLog="$root/logs-clean/$hostTarget.txt"

    #unix shell script, and shell varibles.
    $buildScript="$root/$hostTarget.sh" | Win2Unix
    $vars=@(
        "GODOT=$($godot | Win2Unix)"
        "GODOT_TR=$($godot_tr | Win2Unix)"
        "BUILD_ROOT=$($buildRoot | Win2Unix)"
        "FRESH=$($freshBuild ? "--fresh" : $null)"
        "TEST=$($noTestBuild ? '0' : '1')"
    )
    $vars

    "cmd /c $msys2_shell -c `"$vars $buildScript`" 2>&1" `
        | pwsh -nop -Command - | Tee-Object -FilePath $rawLog

    # Reset the working directory after we are done.
    Set-Location $root

    $matchPattern = '(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern $rawLog | sed -E 's/\s+/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > $cleanLog
}

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
        LocalPrep -buildRoot $buildRoot
        TargetBuild -msys2Env $msys2Env -hostTarget $hostTarget -buildRoot $buildRoot
    }
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below. The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1
