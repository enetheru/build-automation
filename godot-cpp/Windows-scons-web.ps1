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

$emsdk = "C:\emsdk"

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

    H1 "SCons Build"
    Set-Location "$buildRoot/test"

    Format-Command "scons verbose=yes platform=web target=template_release"
    scons verbose=yes platform=web target=template_release
}

function Test {
    H4 "TODO Testing"
}