#!/usr/bin/env pwsh
#Requires -Version 7.4

# PowerShell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

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

# [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
[System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"
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

# Host Platform Values and Functions
. "$root\share\build-actions.ps1"

# Project overrides and functions
function PrepareCommon {

    # Clean up key artifacts to trigger rebuild
    & {
        # ignore the error result from ripgrep not finding any files 
        $PSNativeCommandUseErrorActionPreference = $false
        [array]$artifacts = @($(rg -u --files "$buildRoot" `
            | rg "(memory|example).*?o(bj)?$"))
    
        $artifacts += @($(rg -u --files "$buildRoot" `
            | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))
    
        if( $artifacts.Length -gt 0 ) {
            H3 "Removing key Artifacts"
            $artifacts | Sort-Object | Get-Unique | ForEach-Object {
                Write-Host "Removing $_"
                Remove-Item $_
            }
        }
    }

    # SCons - Remove generated source files if exists.
    if( Test-Path "$buildRoot\gen" -PathType Container ) {
        H4 "Removing Generated Files"
        Remove-Item -LiteralPath "$buildRoot\gen" -Force -Recurse
    }
}

# Clean up Binaries to trigger rebuild
function EraseKeyObjects {
    [array]$binaries = @(Get-ChildItem -Recurse `
        | Where-Object { $_.Name -match "(memory|example).*?o(bj)?$" })
    
    if( $binaries.Length -gt 0 ) {
        H3 "Removing Objects"
        $binaries | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
}

# Clean up Binaries to trigger rebuild
function EraseBinaries {
    [array]$binaries = @(Get-ChildItem -Recurse `
        | Where-Object { $_.Name -match "\.(so|dll|dylib|wasm32|wasm)$" })
    
    if( $binaries.Length -gt 0 ) {
        H3 "Removing Binaries"
        $binaries | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
}

function TestCommon {
    Write-Output "" >> "$targetRoot\summary.log"
    H4 "$config" >> "$targetRoot\summary.log"

    if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        Format-Command "$godot -e --path `"$buildRoot\test\project`" --quit --headless"
        & $godot -e --path "$buildRoot\test\project" --quit --headless 2>&1 | Tee-Object -Variable result
        Start-Sleep -Seconds 1

        if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
            Write-Output "Failed to create .godot folder" >> "$targetRoot\summary.log"
            return 1
        }
    } else {
        H4 "The .godot folder has already been generated."
    }

    H4 "Run the test project"
    Format-Command "$godot_tr --path `"$buildRoot\test\project\`" --quit --headless`n"
    & $godot_tr --path "$buildRoot\test\project\" --quit --headless | Tee-Object -Variable result
    @($result.split( "`r`n" ) | Where-Object { $_ -Match "FINI|PASS|FAIL|Godot" }) >> "$targetRoot\summary.log"
}

# Per config Overrides and functions
. "$targetRoot\$script"

H3 "$config - Processing"

if( $fetch -eq $true ) {
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare -eq $true ) {
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "$config - Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test -eq $true ) {
    $result = ("unknown")
    Test
    ($stats).test = "OK"
}

H2 "$config - Completed"

PrintStats
Start-Sleep 1
