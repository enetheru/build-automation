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

$toolChain="$root\toolchains\w64-mingw-w64.cmake"

function Prepare {
    PrepareCommon
}

function Build {
    H1 "CMake Build"

    H4 "Disabled"
    return

    H4 "Creating build Dir"
    $buildDir="$buildRoot\cmake-build"
    New-Item -Path $buildDir -ItemType Directory -Force
    Set-Location $buildDir

    H4 "CMake Configure"
    if( $fresh ){ $doFresh='--fresh' } else { $doFresh='' }
    Format-Command "cmake $doFresh ..\ -GNinja -DTEST_TARGET=template_release --toolchain $toolChain"
    cmake $doFresh ..\ -GNinja -DTEST_TARGET=template_release --toolchain $toolChain

    H4 "CMake Build"
    Format-Command "cmake --build . -j 12 --verbose -t godot-cpp-test --config Release"
    cmake --build . -j 12 --verbose -t godot-cpp-test --config Release
}

function Test {
    TestCommon
}
