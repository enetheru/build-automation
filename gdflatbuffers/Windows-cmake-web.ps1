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
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    PrepareCommon

    H3 "Update EmSDK"
    Set-Location "C:\emsdk"
    Format-Eval git pull

    # perform any updates to emscripten as required.
    Format-Eval ./emsdk.ps1 install latest

    H3 "Activate EmSDK"
    Format-Eval ./emsdk.ps1 activate latest

    # Create cmake-build directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    H3 "CMake Configure"
    [array]$cmakeVars = "-DCMAKE_BUILD_TYPE=Release"
    Format-Eval "emcmake.bat cmake $doFresh .. $($cmakeVars -Join ' ')"
    
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null
    
    # Check for cmake-build directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        Write-Error "Missing buildDir:'$buildDir'"
    }
    Set-Location $buildDir
    
    $cmakeVars = "-t flatc"
    Format-Eval "cmake --build . $doVerbose $cmakeVars"
    
    $cmakeVars = "-t gdflatbuffers.editor"
    Format-Eval "cmake --build . $doVerbose $cmakeVars"
}