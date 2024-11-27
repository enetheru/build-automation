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

    H4 "Creating build Dir"
    $script:buildDir = "$buildRoot\cmake-build"
    New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    Set-Location $buildDir

    $doFresh = ($fresh) ? "--fresh" : $null
    $doVerbose = ($verbose) ? "-DVERBOSE=ON" : $null
 

    H1 "CMake Configure"
    Format-Command "cmake $doFresh ..\ $doVerbose -DGODOT_DEV_BUILD:YES -DTEST_TARGET=template_release"
    cmake $doFresh ..\ $doVerbose -DGODOT_DEV_BUILD=YES -DTEST_TARGET=template_release
}

function Build {
    H1 "CMake Build"
    Set-Location $buildDir

    $doVerbose = ($verbose) ? "-DVERBOSE=ON" : $null

    $vsExtraOptions = "/nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""

    H3 "Building godot-cpp::template_debug"
    Format-Command "cmake --build . -j 12 --verbose -t template_debug --config Debug -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t template_debug --config Debug -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H3 "Building godot-cpp::template_release"
    Format-Command "cmake --build . -j 12 --verbose -t template_release --config Debug -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t template_release --config Debug -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H3 "Building godot-cpp::editor"
    Format-Command "cmake --build . -j 12 --verbose -t editor --config Debug -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t editor --config Debug -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H4 "Building godot-cpp-test"
    Format-Command "cmake --build . -j 12 --verbose -t godot-cpp-test --config Debug -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t godot-cpp-test --config Debug -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"
}

function Test {
    TestCommon
}
