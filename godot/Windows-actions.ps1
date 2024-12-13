#!/usr/bin/env pwsh
#Requires -Version 7.4

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

function PrintStats {
    @"
(`$statistics).fetch    = "$(($stats).fetch)"
(`$statistics).prepare  = "$(($stats).prepare)"
(`$statistics).build    = "$(($stats).build)"
(`$statistics).test     = "$(($stats).test)"
"@
}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    PrintStats
    Start-Sleep -Seconds 1
}

. "$root/share/format.ps1"

[string]$thisScript = $(Get-PSCallStack)[0].scriptName
$config = Split-Path -Path $script -LeafBase
$targetRoot = $thisScript  | split-path -parent
$buildLeaf = ($config -split "-", 2)[-1]
$buildRoot = "$targetRoot\build-$buildleaf"

[System.Uri]$gitUrl = "http://github.com/godotengine/godot.git"
[string]$gitBranch = "master"

H2 "Build '$target' on '$platform' using '$config'"
Write-Output @"
  envActions  = $thisScript
  buildScript = $script

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test
  
  proc_count  = $jobs

  fresh build = $fresh
  log append  = $append

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot
"@

Set-Location "$targetRoot"

# Source generic actions
. "$root\share\build-actions.ps1"

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

# source config-unique action overrides
. "$targetRoot\$script"

H3 "Processing - $config"

if( $fetch      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Fetch"
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare  -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Prepare"
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Build"
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test       -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Test"
    Test | Tee-Object -Variable result
    ($stats).test = ($result | Select-Object -Last 1)
}

PrintStats

Start-Sleep 1
