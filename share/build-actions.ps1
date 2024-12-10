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
        Format-Eval git config remote.origin.fetch 'refs/heads/*:refs/heads/*'
    }
    Set-Location "$targetroot\git"
    
    Format-Eval git fetch -u --force --all
    
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        Format-Eval git worktree add --force "$buildRoot" "$gitBranch"
        Format-Eval git config remote.origin.fetch 'refs/heads/*:refs/heads/*'
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    Format-Eval git fetch -u --force
    Format-Eval git reset --hard
    Format-Eval git status

    #TODO fix when the tree diverges and needs to be clobbered.
    
    
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
