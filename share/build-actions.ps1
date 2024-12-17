#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

##################################- Utilities -#################################
#                                                                            #
#        ██    ██ ████████ ██ ██      ██ ████████ ██ ███████ ███████         #
#        ██    ██    ██    ██ ██      ██    ██    ██ ██      ██              #
#        ██    ██    ██    ██ ██      ██    ██    ██ █████   ███████         #
#        ██    ██    ██    ██ ██      ██    ██    ██ ██           ██         #
#         ██████     ██    ██ ███████ ██    ██    ██ ███████ ███████         #
#                                                                            #
################################################################################

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

function SummariseConfig {
    H2 "Build '$target' on '$platform' using '$config'"
    Write-Output @"
  envActions  = $thisScript
  buildScript = $script

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test
  
  proc_count  = $jobs
  fresh build = $fresh
  log append  = $append

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot
"@
}

##################################- updates -###################################
#                                                                            #
#         ██    ██ ██████  ██████   █████  ████████ ███████ ███████          #
#         ██    ██ ██   ██ ██   ██ ██   ██    ██    ██      ██               #
#         ██    ██ ██   ██ ██████  ███████    ██    █████   ███████          #
#         ██    ██ ██   ██ ██      ██   ██    ██    ██           ██          #
#          ██████  ██████  ██      ██   ██    ██    ███████ ███████          #
#                                                                            #
################################################################################

# Update Android
function UpdateAndroid {
    H3 "Update Android SDK"
    
    $cmdlineTools="C:\androidsdk\cmdline-tools\latest\bin"
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    $env:Path = "$cmdlineTools;" + $env:Path
    
    Format-Eval "sdkmanager --update $doVerbose"
}

function UpdateEmscripten {
    H3 "Update Emscripten SDK"
    
    $emsdk = "C:\emsdk"
    
    Set-Location $emsdk
    Format-Eval git pull
    Format-Eval $emsdk\emsdk.ps1 install latest
}

####################################- Fetch -###################################
#                                                                            #
#                  ███████ ███████ ████████  ██████ ██   ██                  #
#                  ██      ██         ██    ██      ██   ██                  #
#                  █████   █████      ██    ██      ███████                  #
#                  ██      ██         ██    ██      ██   ██                  #
#                  ██      ███████    ██     ██████ ██   ██                  #
#                                                                            #
################################################################################
function Fetch {
    # Create worktree is missing
    if( -Not (Test-Path -Path "$buildRoot" -PathType Container) ) {
        H3 "Create WorkTree"
        Format-Eval git --git-dir="$targetRoot/git" worktree add -d "$buildRoot"
    } else {
        H3 "Update WorkTree"
    }
    
    # Update worktree
    Set-Location "$buildRoot"
    Format-Eval git checkout --force -d $gitBranch
    Format-Eval git status
}

##################################- Prepare -###################################
#                                                                            #
#          ██████  ██████  ███████ ██████   █████  ██████  ███████           #
#          ██   ██ ██   ██ ██      ██   ██ ██   ██ ██   ██ ██                #
#          ██████  ██████  █████   ██████  ███████ ██████  █████             #
#          ██      ██   ██ ██      ██      ██   ██ ██   ██ ██                #
#          ██      ██   ██ ███████ ██      ██   ██ ██   ██ ███████           #
#                                                                            #
################################################################################

function Prepare {
    H3 "No Prepare Action Specified"
    Write-Output "-"
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

####################################- Build -###################################
#                                                                            #
#                    ██████  ██    ██ ██ ██      ██████                      #
#                    ██   ██ ██    ██ ██ ██      ██   ██                     #
#                    ██████  ██    ██ ██ ██      ██   ██                     #
#                    ██   ██ ██    ██ ██ ██      ██   ██                     #
#                    ██████   ██████  ██ ███████ ██████                      #
#                                                                            #
################################################################################

function Build {
    H3 "No Build Action Specified"
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
        Figlet -f "small" "SCons Build"
        H3 "Config: $config"
        H3 "Target: $target"
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

function BuildCMake {
    param(
        [Alias( "t" )] [array] $targets = @("all"),
        [Alias( "v" )] [array] $vars = @(),
        [Alias( "e" )] [array] $extra = @()
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
        Figlet -f "small" "CMake Build"
        H3 "Config: $config"
        H3 "Target: $target"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval cmake --build . $buildOpts -t "$target" "--" "$extraOpts"
        
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

####################################- Test -####################################
#                                                                            #
#                     ████████ ███████ ███████ ████████                      #
#                        ██    ██      ██         ██                         #
#                        ██    █████   ███████    ██                         #
#                        ██    ██           ██    ██                         #
#                        ██    ███████ ███████    ██                         #
#                                                                            #
################################################################################

function Test {
    H3 "No Test Action Specified"
    Write-Output "-"
}

##################################- Process -###################################
#                                                                            #
#          ██████  ██████   ██████   ██████ ███████ ███████ ███████          #
#          ██   ██ ██   ██ ██    ██ ██      ██      ██      ██               #
#          ██████  ██████  ██    ██ ██      █████   ███████ ███████          #
#          ██      ██   ██ ██    ██ ██      ██           ██      ██          #
#          ██      ██   ██  ██████   ██████ ███████ ███████ ███████          #
#                                                                            #
################################################################################

function DefaultProcess {
    if( $fetch ) {
        $Host.UI.RawUI.WindowTitle = "Fetch - $config"
        $stats | Add-Member -MemberType NoteProperty -Name 'fetch' -Value 'Fail'
        
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        Fetch
        $timer.Stop();
        
        $stats.fetch = "OK"
        $stats | Add-Member -MemberType NoteProperty -Name 'fetchDuration' -Value $timer.Elapsed
        H3 "$config - Fetch Duration: $($timer.Elapsed)"
    }
    
    if( $prepare ) {
        $Host.UI.RawUI.WindowTitle = "Prepare - $config"
        $stats | Add-Member -MemberType NoteProperty -Name 'prepare' -Value 'Fail'
        
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        Prepare
        $timer.Stop();
        
        $stats.prepare = "OK"
        $stats | Add-Member -MemberType NoteProperty -Name 'prepareDuration' -Value $timer.Elapsed
        H3 "$config - Prepare Duration: $($timer.Elapsed)"
    }
    
    if( $build ) {
        $Host.UI.RawUI.WindowTitle = "Build - $config"
        $stats | Add-Member -MemberType NoteProperty -Name 'build' -Value 'Fail'
        
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        Build
        $timer.Stop();
        
        $stats.build = "OK"
        $stats | Add-Member -MemberType NoteProperty -Name 'buildDuration' -Value $timer.Elapsed
        H3 "$config - Build Duration: $($timer.Elapsed)"
    }
    
    if( $test ) {
        $stats | Add-Member -MemberType NoteProperty -Name 'test' -Value 'Fail'
        $Host.UI.RawUI.WindowTitle = "Test - $config"
        
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        Test
        $timer.Stop();
        
        $stats.test = "OK"
        $stats | Add-Member -MemberType NoteProperty -Name 'testDuration' -Value $timer.Elapsed
        H3 "$config - Test Duration: $($timer.Elapsed)"
    }
}

function Finalise {
    param ( [PSCustomObject]$stats )
    Write-Host "Output Stats:"
    
    foreach( $stat in $stats.psobject.properties ){
        Write-Host ('$statistics | Add-Member -Force -MemberType NoteProperty -Name "{0}" -Value "{1}"' `
            -f $stat.Name, $stat.Value )
    }
    
    Fill "_   " | Right " EOF "
}