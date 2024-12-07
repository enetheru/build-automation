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

    # Create cmake-build directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path "$buildDir" -ItemType Directory -Force | Out-Null
    }
    Set-Location "$buildDir"

    H3 "CMake Configure"
    $cmakeVars = $null
    Format-Eval "cmake $doFresh .. $cmakeVars"
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null

    # Check for cmake-build directory
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        Write-Error "Missing buildDir:'$buildDir'"
    }

    Set-Location $buildDir

    $vsExtraOptions = "-- /nologo /v:m /clp:'ShowCommandLine;ForceNoAlign'"

    $cmakeVars = "-t flatc --config Release"
    Format-Eval "cmake --build . $doVerbose $cmakeVars $vsExtraOptions"

    $cmakeVars = "-t gdflatbuffers.template_debug --config Release"
    Format-Eval "cmake --build . $doVerbose $cmakeVars $vsExtraOptions"

    # TODO Add artifact summary, like name, size,
}

function Test {
    H1 "Test"
    TestCommon
}
