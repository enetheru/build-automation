#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Error "Do not run this script directly, it simply holds helper functions"
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    H4 "Using Default env Settings"
    return
}

[string]$gitBranch = "4.3"

function Prepare {
    H3 "Prepare"
    
    if( -Not (Test-Path -Path "$targetRoot\git" -PathType Container) ) {
        Write-Error "bare git repo is missing."
    }
    
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        Set-Location "$targetRoot\git"
        Format-Eval git worktree add "$buildRoot" "$gitBranch"
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    $status = $(git status)
    if( $status | ForEach-Object { $_ -Match "Changes not staged for commit" } ){
        Format-Eval "git reset --hard"
    } else {
        Write-Error $status
    }
    
    # DeleteBuildArtifacts
}

function Build {
    H1 "SCons Build"
    $doVerbose = ($verbose -eq $true) ? "verbose=yes" : $null
    
    
    H4 "Changing directory to '$buildRoot'"
    Set-Location "$buildRoot"
    Format-Eval "scons -j$jobs $doVerbose target=template_debug"
    Format-Eval "scons -j$jobs $doVerbose target=template_release"
    Format-Eval "scons -j$jobs $doVerbose target=editor"
}
