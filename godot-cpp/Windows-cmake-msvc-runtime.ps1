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

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    $doVerbose = ($verbose) ? "--verbose" : $null
    $doFresh = ($fresh) ? "--fresh" : $null

    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    # Build Default
    $buildDir = "$buildRoot/cmake-build-default"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. "
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Release -- $MSBuildOptions"

    # Build with DEBUG_CRT=yes
    $buildDir = "$buildRoot/cmake-build-debug_crt"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_DEBUG_CRT=YES"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Release -- $MSBuildOptions"

    # Build with USE_STATIC=NO
    $buildDir = "$buildRoot/cmake-build-static"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_USE_STATIC_CPP=NO"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Release -- $MSBuildOptions"

}
