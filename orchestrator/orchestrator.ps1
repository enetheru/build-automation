#!/usr/bin/env pwsh
#Requires -Version 7.4

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# [System.Uri]$sourceOrigin = "https://github.com/CraterCrash/godot-orchestrator.git"
[System.Uri]$sourceOrigin = "C:\Godot\extensions\godot-orchestrator"
#[string]$sourceBranch = "2.0"
#[string]$sourceHash = "e4ef00d9ed8ad67b876f0e6223b03bd7b2fc3d93" #2.0.4.stable
[string]$sourceBranch = "2.1-modernise"
#[string]$sourceHash = "d091f26c28de2b7108c9890f2b97b901795fa151" # 2.1.2.stable

# Local prep function for orchestrator.
function Prepare {
    param(
        [Parameter(Mandatory=$true)][string]$buildRoot
    )
    "== Prepare =="
    Set-Location $buildRoot

    "- Update Submodules"
    if( -Not (Test-Path extern/godot-cpp/*) ) {
        git submodule update --init --remote extern/godot-cpp
    }

    set-location extern/godot-cpp
    if( -Not (git remote -v | Select-String -Pattern "local" -Quiet ) ){
        git remote add local C:\godot\src\godot-cpp
        git fetch local
    }

    if( -Not (git branch | Select-String -Pattern "4.3-modernise" -Quiet ) ){
        git checkout "local/4.3-modernise" --track
    }

    set-location $root

    "-- Remove any remaining key build artifacts"
    # Remove key build artifacts before re-build
    # Disable: Exit failure on Non-Zero exit code for ripgrep finding no results
    $PSNativeCommandUseErrorActionPreference = $false
    rg -u --files | rg "\.(dll|so|wasm|dylib|lib)$" | ForEach-Object { Remove-Item $_ }
    rg -u --files | rg "orchestration.*?\.(o|obj|so)$" | ForEach-Object { Remove-Item $_ }
    # Enable: Exit failures on Non-Zero exit code
    $PSNativeCommandUseErrorActionPreference = $true
}

function Test {
    param(
        [Parameter(Mandatory=$true)][string]$buildRoot
    )
    Write-Output "Nothing to test"
#    if( -Not $test ) {
#        # Generate the .godot folder
#        &$godot -e --path "$buildRoot/test/Project" --headless --quit *> $null
#        # Run test project
#        &$godot_tr --path "$buildRoot/test/Project" --headless --quit
#    }
}