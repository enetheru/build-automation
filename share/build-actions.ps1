#!/usr/bin/env pwsh
#Requires -Version 7.4


# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

function Fetch {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    H1 "Git Fetch"
    Write-Output "  Target Root   = $targetRoot"
    Write-Output "  Build Root    = $buildRoot"
    Write-Output "  Git URL       = $gitUrl"
    Write-Output "  Git Branch    = $gitBranch"

    if( -Not (Test-Path "$buildRoot" -PathType Container) ) {
        H4 "Creating $buildRoot"
        New-Item -Force -ItemType Directory -Path "$buildRoot"
    }

    # Clone if not already
    if( -Not (Test-Path -Path "$buildRoot/*") ) {
        H4 "Cloning $target"
        Format-Eval git "clone $gitUrl `"$buildRoot`""
        if( $LASTEXITCODE ){
            Write-Error "Clone Failure"
        }
    }

    # Change working directory
    Set-Location "$buildRoot"

    # Fetch any changes and reset to latest
    [bool]$fetchNeeded = $(git fetch --dry-run 2>&1)
    [string]$currentBranch = $(git branch --show-current) 
    [bool]$wrongBranch = -Not ($currentBranch -match $gitBranch)

    if( $fetchNeeded -Or $wrongBranch ){
        H4 "Fetching Latest"
        git fetch --all
        git reset --hard '@{u}'
        if( $gitBranch ) {
            git checkout "$gitBranch"
        }
    }

    #TODO fix when the tree diverges and needs to be clobbered.
    H4 "Git Status"
    git status
    Set-Location "$targetRoot"
}

function Prepare {
}

function Build {
}

function Test {
}

function Clean {
}
