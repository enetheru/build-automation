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


$script:buildDebug = ''
$script:buildDev = ''

function Prepare {
    PrepareCommon

    $doFresh = ($fresh) ? "--fresh" : $null

    $script:buildDebug = "$buildRoot/cmake-build-debug"
    $buildDir = $script:buildDebug
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }

    $script:buildDev = "$buildRoot/cmake-build-dev"
    $buildDir = $script:buildDev
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }

    Set-Location $buildDebug
    Format-Eval cmake "$doFresh .."

    Set-Location $buildDev
    Format-Eval cmake "$doFresh .. -DGODOT_DEV_BUILD=YES"
}

function Build {
    H1 "CMake Build"

    $doVerbose = ($verbose) ? "--verbose" : $null
    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    Set-Location $buildDebug
    # scons target=template_debug debug_symbols=yes"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"

    Set-Location $buildDev
    # scons target=template_debug dev_build=yes"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Debug -- $MSBuildOptions"

    # scons target=template_debug dev_build=yes debug_symbols=no"
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config Release -- $MSBuildOptions"
}
