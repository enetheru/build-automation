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
    $doFresh = ($fresh) ? "--fresh" : $null

    $script:buildDir = "$buildRoot/cmake-build-default"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. "
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose) ? "--verbose" : $null
    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    Set-Location $buildDir
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config RelWithDebInfo -- $MSBuildOptions"
}
