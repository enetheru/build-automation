#!/usr/bin/env pwsh
#Requires -Version 7.4

# PowerShell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

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
    Fetch 2>&1
}

if( $prepare -eq $true ) {
    Prepare 2>&1
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
    Test 2>&1 | Tee-Object -Variable result
    if( @($result | Where-Object { $_ })[-1] -Match "PASSED" ) {
        Write-Output "$config - Test Succeded"
    } else {
        Write-Output "$config - Test-Failure"
    }
}

H2 "$config - Completed"
Start-Sleep 1
