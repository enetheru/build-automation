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
    Format-Eval cmake "$doFresh .. $doVerbose -DGODOT_DEV_BUILD=YES"
}

function Build {
    H1 "CMake Build"

    H4 "Changing directory to $buildDir"
    Set-Location $buildDir

    $doVerbose = ($verbose) ? "--verbose" : $null
    $doFresh = ($fresh) ? "--fresh" : $null

    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    foreach( $target in ("template_debug", "template_release", "editor") ) {
        H3 "Building godot-cpp::$target | Config = Debug"
        Format-Eval cmake "--build . $doVerbose -t $target --config Debug -- $MSBuildOptions"
    }

    foreach( $target in ("template_debug", "template_release", "editor") ) {
        H3 "Building godot-cpp-test | target=$target"
        Format-Eval cmake ".. -DGODOT_DEV_BUILD=YES -DTEST_TARGET=$target"
        Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"
    }
}

function Test {
    TestCommon
}
