#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ){
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$emsdk="C:\emsdk"

function Prepare {
    PrepareCommon

    H1 "Update EmSDK"
    Set-Location $emsdk
    git pull

    # perform any updates to emscripten as required.
    &"$emsdk\emsdk.ps1" install latest
}

function Build {
    H4 "Activate EmSDK"
#    Set-Location $emsdk
    &"$emsdk\emsdk.ps1" activate latest

    H1 "CMake Build"

    H4 "Creating build Dir"
    $buildDir="$buildRoot\cmake-build"
    New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    Set-Location $buildDir

    H4 "CMake Configure"
    if( $fresh ){ $doFresh='--fresh' } else { $doFresh='' }
    Format-Command "emcmake.bat cmake $doFresh ..\ -DTEST_TARGET=template_release"
    emcmake.bat cmake $doFresh ..\ -DTEST_TARGET=template_release

    H4 "CMake Build"
    Format-Command "cmake --build . -j 12 --verbose -t godot-cpp-test --config Release"
    cmake --build . -j 12 --verbose -t godot-cpp-test --config Release
}

function Test {
    H4 "TODO Testing"
}