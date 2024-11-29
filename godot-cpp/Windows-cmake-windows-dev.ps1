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

    $script:buildDir = "$buildRoot\cmake-build"

    if( -Not (Test-Path -Path $script:buildDir -PathType Container) ) {
        H4 "Creating build Dir"
        Format-Command "New-Item -Path $buildDir -ItemType Directory -Force"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    $doFresh = ($fresh) ? "--fresh" : $null
    $doVerbose = ($verbose) ? "-DVERBOSE=ON" : $null

    H1 "CMake Configure"
    Format-Eval cmake "$doFresh .. $doVerbose -DGODOT_DEV_BUILD=YES -DTEST_TARGET=template_release"
}

function Build {
    H1 "CMake Build"

    H4 "Changing directory to $buildDir"
    Set-Location $buildDir

    $doVerbose = ($verbose) ? "--verbose" : $null

    $MSBuildOptions = "/nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""

    foreach( $target in ("template_debug", "template_release", "editor", "godot-cpp-test") ) {
        H2 "Building godot-cpp::$target | Config = Debug"
        Format-Eval cmake "--build . -j 12 $doVerbose -t $target --config Debug -- $MSBuildOptions"
    }
}

function Test {
    TestCommon
}
