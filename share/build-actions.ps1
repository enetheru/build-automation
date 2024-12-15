#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# Update Android
function UpdateAndroid {
    H3 "Update Android SDK"
    
    $cmdlineTools="C:\androidsdk\cmdline-tools\latest\bin"
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    $env:Path = "$cmdlineTools;" + $env:Path
    
    Format-Eval "sdkmanager --update $doVerbose *> $null"
}

function UpdateEmscripten {
    H3 "Update Emscripten SDK"
    
    $emsdk = "C:\emsdk"
    
    Set-Location $emsdk
    Format-Eval git pull
    Format-Eval $emsdk\emsdk.ps1 install latest
}

function EraseFiles {
    param(
        [Alias( "f" )] [string] $fragments = "NothingToErase",
        [Alias( "e" )] [string] $ext = ""
    )
    
    [array]$artifacts = @(Get-ChildItem -Recurse `
        | Where-Object { $_.Name -match "($fragments).*\.($ext)$" })
    
    if( $artifacts.Length -gt 0 ) {
        H3 "Erase Files"
        Write-Warning "Deleting $($artifacts.Length) Artifacts"
        $artifacts | ForEach-Object {
            Write-Host "  Removing '$_'"
            Remove-Item "$_"
        }
    }
}

function Fetch {
    # The expectation is that we are in $targetRoot
    # and when we finish we should be back in $targetRoot
    Figlet "Git Fetch"
    Write-Output "  Target Root   = $targetRoot"
    Write-Output "  Build Root    = $buildRoot"
    Write-Output "  Git URL       = $gitUrl"
    Write-Output "  Git Branch    = $gitBranch"
    
    H3 "Update Repository"
    
    # Clone if not already
    if( -Not (Test-Path -Path "$targetRoot\git" -PathType Container) ) {
        Format-Eval git clone --bare "$gitUrl" "$targetroot\git"
    } else {
        Format-Eval git --git-dir=$targetRoot\git fetch --force origin *:*
        Format-Eval git --git-dir=$targetRoot\git worktree prune
        Format-Eval git --git-dir=$targetRoot\git worktree list
    }
    
    H3 "Update WorkTree"
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        Format-Eval git --git-dir="$targetRoot/git" worktree add -d "$buildRoot"
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    Format-Eval git checkout --force -d $gitBranch
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

## Build with SCons
# Function takes two arguments, array of targets, and array of options.
# if both unset, then default build options are used.
function BuildSCons {
    param(
        [Alias( "v" )] [array] $vars = @(),
        [Alias( "t" )] [array] $targets = @()
    )
    
    # requires SConstruct file existing in the current directory.
    # SCons - Remove generated source files if exists.
    if( -Not (Test-Path "SConstruct" -PathType Leaf) ) {
        Write-Error "BuildSCons: Missing '$(Get-Location)\SConstruct'"
        Return 1
    }
    
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    
    $buildVars = @( "$doJobs", "$doVerbose") + $vars
    
    foreach( $target in $targets ){
        Figlet -f "small" "SCons Build"; H3 "target: $target"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "scons $($buildVars -Join ' ') target=$target"
        
        $timer.Stop()
        $ts = $timer.Elapsed
        $duration = "{0:00}:{1:00}:{2:00}" -f $ts.Hours, $ts.Minutes, $ts.Seconds
        
        $newStat = [PSCustomObject] @{
            tool        = "scons"
            target      = "$target"
            duration    = $duration
        }
        $statArrayRef.Value += $newStat
        
        H3 "BuildScons Completed"
        $newStat | Format-Table
        
        Fill "-"
    }
}

# Prepare with CMake
function PrepareCMake {
    param (
        [Alias( "v" )] [array] $vars = @(),
        [Alias( "b" )] [string] $buildDir = "cmake-build"
    )
    
    # requires CMakeLists.txt file existing in the current directory.
    if( -Not (Test-Path "CMakeLists.txt" -PathType Leaf) ) {
        Write-Error "PrepareCMake: Missing '$(Get-Location)\CMakeLists.txt'"
        Return 1
    }
    
    Figlet -f "small" "CMake Prepare"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null
    
    # Create Build Directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path "$buildDir" -ItemType Directory -Force | Out-Null
    }
    Set-Location "$buildDir"
    
    Format-Eval cmake $doFresh .. $($vars -Join ' ')
}

function BuildCMake {
    param(
        [Alias( "v" )] [array] $vars = @(),
        [Alias( "e" )] [array] $extra = @(),
        [Alias( "t" )] [array] $targets = @("all")
    )
    
    # requires SConstruct file existing in the current directory.
    # SCons - Remove generated source files if exists.
    if( -Not (Test-Path "CMakeCache.txt" -PathType Leaf) ) {
        Write-Error "Missing '$(Get-Location)\ CMakeCache.txt'"
        Return 1
    }
    
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    $buildOpts = "$doJobs $doVerbose $($vars -Join ' ')"
    $extraOpts = "$($extra -Join ' ')"
    
    foreach( $target in $targets ){
        Figlet -f "small" "CMake Build"; H3 "target: $target"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval cmake --build . $buildOpts -t "$target" -- $extraOpts
        
        $timer.Stop()
        $ts = $timer.Elapsed
        $duration = "{0:00}:{1:00}:{2:00}" -f $ts.Hours, $ts.Minutes, $ts.Seconds
        
        $newStat = [PSCustomObject] @{
            tool        = "cmake"
            target      = "$target"
            duration    = $duration
        }
        $statArrayRef.Value += $newStat
        
        H3 "BuildScons Completed"
        $newStat | Format-Table
        
        Fill "-"
    }
}