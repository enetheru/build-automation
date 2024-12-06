#!/usr/bin/env pwsh
#Requires -Version 7.4

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$statsSchema = @{
    fetch   = ($fetch -eq $true) ? "Fail" : "-"
    prepare = ($prepare -eq $true) ? "Fail" : "-"
    build   = ($build -eq $true) ? "Fail" : "-"
    test    = ($test -eq $true) ? "Fail" : "-"
}
$stats = [PSCustomObject]$statsSchema

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

H2 "Build '$target' on '$platform' using '$config'"
Write-Output @"
  envActions  = $thisScript
  buildScript = $script

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test

  fresh build = $fresh
  log append  = $append

  target      = $target
  branch      = $gitBranch
"@

# Main Variables
[string]$godot = "C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr = "C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

Write-Output @"

  godot.editor           = $godot
  godot.template_release = $godot_tr
"@

# [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp-test.git"
[System.Uri]$gitUrl = "C:\Godot\src\godot-cpp-test"
# [string]$gitBranch = "ipo-lto"

Write-Output @"

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch
"@

# Get the target root from this script location
$targetRoot = $thisScript  | split-path -parent
$buildRoot = "$targetRoot\$config"

Write-Output @"

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot
"@

Set-Location "$targetRoot"

# Some steps are identical.
function PrepareCommon {

    # Clean up key artifacts to trigger rebuild
    [array]$artifacts = @($(rg -u --files "$buildRoot" `
        | rg "(memory|example).*?o(bj)?$"))

    $artifacts += @($(rg -u --files "$buildRoot" `
        | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))
    #    ($array1 + $array2) | Select-Object -Unique -Property Name

    #Ignore exit code from ripgrep failure to match files.
    $global:LASTEXITCODE = 0

    if( $artifacts.Length -gt 0 ) {
        H3 "Removing key Artifacts"
        $artifacts | Sort-Object | Get-Unique | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }

    # SCons - Remove generated source files if exists.
    if( Test-Path "$buildRoot\gen" -PathType Container ) {
        H4 "Removing Generated Files"
        Remove-Item -LiteralPath "$buildRoot\gen" -Force -Recurse
    }
}

function TestCommon {
    Write-Output "" >> "$targetRoot\summary.log"
    H4 "$config" >> "$targetRoot\summary.log"

    $projectDir = "$buildRoot\project"

    if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        & {
            $PSNativeCommandUseErrorActionPreference = $false
            &$godot -e --path "$projectDir" --quit --headless *> $null
            # Godot spawns and detaches another process, making this harder than it needs to be.
            # FIXME find a way to get the actual process ID that I want to wait on.
            while( Get-Process | Where-Object -Property "ProcessName" -Match "godot" ) {
                #This is a slightly better fix than before, but I still want to get the specific process.
                Start-Sleep -Seconds 1
            }
        }
        if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
            Write-Error "Failed to create .godot folder" >> "$targetRoot\summary.log"
        }
    }
    
    H4 "Run the test project"
    $result = ("unknown")
    &$godot_tr --path "$projectDir" --quit --headless  | Out-String | Tee-Object -Variable result
    if( @($result | Where-Object { $_ })[-1] -Match "PASSED" ) {
        Write-Output "Test Succeded"
    } else {
        Write-Error "Test-Failure"
    }
}

H3 "Processing - $config"

# Source generic actions, and then override.
. "$root\share\build-actions.ps1"
. "$targetRoot\$script"

if( $fetch      -eq $true ) {
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare  -eq $true ) {
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test       -eq $true ) {
    Test
    ($stats).test = "OK"
}

PrintStats

Start-Sleep 1