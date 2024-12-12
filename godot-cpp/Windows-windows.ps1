#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    H4 "Using Default env Settings"
    return
}

$script:buildDir = "$buildRoot/cmake-build"

function Prepare {
    H1 "Prepare"
    
    H3 "CMake Configure"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null
    
    # Create Build Directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir
    
    # CMake Configure
    [array]$cmakeVars = @(
        "-DGODOT_ENABLE_TESTING=YES"
    )
    
    Format-Eval cmake $doFresh .. $($cmakeVars -Join ' ')
}

function Build {
    [array]$statArray = @()
    
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    # FIXME get arch somehow.
    $arch = "x86" + ([Environment]::Is64BitOperatingSystem) ? "_64" : ""
    
    $targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    
    # Build Targets using SCons
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    
    [array]$sconsVars = @()
    
    Set-Location "$buildRoot/test"
    foreach( $target in $targets ){
        H2 "$target"; H1 "Scons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()

        Format-Eval "scons $doJobs $doVerbose target=$target $($sconsVars -Join ' ')"
        
        $timer.Stop()
#        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$target.$arch.so"
        
        $newStat += [PSCustomObject] @{
            target      = "scons.$target"
            duration    = $timer.Elapsed
#            size        = DisplayInBytes $artifact.Length
        }
        $newStat | Format-Table
        $statArray += $newStat
    }
    
    # Build Targets using CMake
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    [array]$cmakeVars = @(
        "$doVerbose",
        "$doJobs",
        "--config Release"
    )
    $vsExtraOptions = "-- /nologo /v:m /clp:'ShowCommandLine;ForceNoAlign'"
    
    Set-Location "$buildDir"
    foreach( $target in $targets ){
        H2 "$target"; H1 "CMake Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval cmake --build . -t godot-cpp.test.$target `
            $($cmakeVars -Join ' ') $vsExtraOptions
        
        $timer.Stop()
#        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$arch.$target.$arch.so"
        
        $newStat += [PSCustomObject] @{
            target      = "cmake.$target"
            duration    = $timer.Elapsed
#            size        = DisplayInBytes $artifact.Length
        }
        $newStat | Format-Table
        $statArray += $newStat
    }

    # Report Results
    $statArray | Format-Table
}