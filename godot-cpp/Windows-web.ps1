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
$script:emsdk = "C:\emsdk"

function Prepare {
    H1 "Prepare"
    
    H4 "Update EmSDK"
    Set-Location $emsdk
    Format-Eval git pull
    Format-Eval $emsdk\emsdk.ps1 install latest
    
    # CMake Configure
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null
    
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path "$buildDir" -ItemType Directory -Force | Out-Null
    }
    Set-Location "$buildDir"
    
    H3 "Activate EmSDK"
    Format-Eval ./emsdk.ps1 activate latest
    
    H1 "CMake Configure"
    [array]$cmakeVars = @(
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGODOT_ENABLE_TESTING=YES",
        "-GNinja"
    )
    
    Format-Eval emcmake.bat cmake $doFresh .. $($cmakeVars -Join ' ')
}

function Build {
    [array]$statArray = @()
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    
    # SCons build
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    [array]$sconsVars = @(
        "$doVerbose",
        "$doJobs",
        "platform=web"
    )
    
    Set-Location "$buildRoot/test"
    
    foreach( $target in $targets ){
        H2 "$target"; H1 "Scons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()

        Format-Eval "scons target=$target $($sconsVars -Join ' ')"
        
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
    
    [array]$sconsVars = @(
        "$doVerbose",
        "$doJobs"
    )
    
    Set-Location $buildDir
    foreach( $target in $targets ){
        H2 "$target"; H1 "CMake Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval emcmake.bat cmake --build . `
            -t godot-cpp.test.$target $($cmakeVars -Join ' ')
        
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