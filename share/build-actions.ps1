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
    
    # Clone if not already
    if( -Not (Test-Path -Path "$targetRoot\git" -PathType Container) ) {
        Format-Eval git clone --bare "$gitUrl" "$targetroot\git"
    }
    # FIXME Update the clone
#    Format-Eval git --git-dir "$targetRoot\git" fetch -u --force --all
    
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        Format-Eval git --git-dir "$targetRoot/git" worktree add -d "$buildRoot"
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    Format-Eval git reset --hard
    Format-Eval git checkout -d $gitBranch
    Format-Eval git status
}

function Prepare {
    H3 "No Prepare Actions Specified"
    Write-Output "-"
}

function Build {
    H3 "No Build Actions Specified"
    Write-Output "-"
}

function Test {
    H3 "No Test Actions Specified"
    Write-Output "-"
}

function Clean {
    H3 "No Clean Actions Specified"
    Write-Output "-"
}
