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
    H3 "No Prepare Action Specified"
    Write-Output "-"
}

function Build {
    H3 "No Build Action Specified"
    Write-Output "-"
}

function Test {
    H3 "No Test Action Specified"
    Write-Output "-"
}

function Clean {
    H3 "No Clean Action Specified"
    Write-Output "-"
}

function CleanLog {
    H3 "Cleaning $args"
    # Clean the logs
    # it goes like this, for each line that matches the pattern.
    # split each line along spaces.
    # [repeated per type of construct] re-join lines that match a set of tags
    # the remove the compiler defaults, since CMake adds so many.
    
    $matchPattern = '^lib|^link|memory|Lib\.exe|link\.exe|  󰞷'
    [array]$compilerDefaults = (
    "fp:precise",
    "Gd", "GR", "GS",
    "Zc:forScope", "Zc:wchar_t",
    "DYNAMICBASE", "NXCOMPAT", "SUBSYSTEM:CONSOLE", "TLBID:1",
    "errorReport:queue", "ERRORREPORT:QUEUE", "EHsc",
    "diagnostics:column", "INCREMENTAL", "NOLOGO", "nologo")
    & {
        $PSNativeCommandUseErrorActionPreference = $false
        rg -M2048 $matchPattern "$args" `
            | sed -E 's/ +/\n/g' `
            | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' `
            | sed -E ':a;$!N;s/(Program|Microsoft|Visual|vcxproj|->)\n/\1 /;ta;P;D' `
            | sed -E ':a;$!N;s/(\.\.\.|omitted|end|of|long)\n/\1 /;ta;P;D' `
            | sed -E "/^\/($($compilerDefaults -Join '|'))$/d"
    }
}