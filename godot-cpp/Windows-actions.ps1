#!/usr/bin/env pwsh
#Requires -Version 7.4

# Because CLion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.

trap {
    Write-Output "trap triggered on exception. Sleeping 1"
    Set-Location $root
    Start-Sleep -Seconds 1
}

# PowerShell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

. "$root/share/format.ps1"

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$config = Split-Path -Path $script -LeafBase


H2 "Build $target using $platform"
Write-Output @"
  thisScript  = $thisScript
  fetch       = $fetch
  configure   = $configure
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
Write-Output @"

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
"@

cd "$targetRoot"



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
        $artifacts | Sort-Object | Get-Unique | %{
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
    H1 "Test"

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
    @($result.split( "`r`n" ) | ? { $_ -Match "FINI|PASS|FAIL|Godot" }) >> "$targetRoot\summary.log"
}

H2 "Processing - $config"

$buildRoot = "$targetRoot\$config"
Write-Output "  buildRoot  = $buildRoot"

. "$root\share\build-actions.ps1"
. "$targetRoot\$script"

if( $fetch ) {
    Fetch 2>&1
    if( $LASTEXITCODE ) {
        Write-Error "Fetch-Failure"
    }
}

if( $configure ) {
    Prepare 2>&1
    if( $LASTEXITCODE ) {
        Write-Error "Prep-Failure"
    }
}

if( $build ){
    Build 2>&1
    if( $LASTEXITCODE ) {
        Write-Error "build-Failure"
    }
}

if( $test ){
    $result=("unknown")
    Test 2>&1 | Tee-Object -Variable result
    if( @($result | ? { $_ })[-1] -Match "PASSED" ) {
        Write-Output "Test Succeded"
    } else {
        Write-Output "Test-Failure"
    }
}

H3 "Completed - $config"
