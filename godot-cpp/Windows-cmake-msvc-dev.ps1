#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


$script:buildDir = ''

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    $doVerbose = ($verbose) ? "--verbose" : $null
    $doFresh = ($fresh) ? "--fresh" : $null

    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    # == Build Default ==
    $buildDir = "$buildRoot/cmake-build-default"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. "
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"

    # == Build with GODOT_DEV_BUILD=yes ==
    $buildDir = "$buildRoot/cmake-build-dev_build"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_DEV_BUILD=YES"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"

    # == Build with GODOT_DEBUG_SYMBOLS=yes ==
    $buildDir = "$buildRoot/cmake-build-debug"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_DEBUG_SYMBOLS=YES"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"


    # == Build with GODOT_DEV_BUILD=YES GODOT_DEBUG_SYMBOLS=NO ==
    $buildDir = "$buildRoot/cmake-build-dev-strip"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_DEBUG_SYMBOLS=YES -DGODOT_DEBUG_SYMBOLS=NO"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"

}
