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
    H1 "SCons Build"

    H4 "Changing directory to $buildRoot/test"
    Set-Location "$buildRoot/test"

    $doVerbose = ($verbose) ? "verbose=yes" : $null
    $target = "target=template_debug"
    $buildProfile = "build_profile=build_profile.json"
    $sconsOptions = "$doVerbose $target $buildProfile"

    # build with dev_build=yes
    format-eval scons "$sconsOptions debug_symbols=yes"

    # build with dev_build=yes
    format-eval scons "$sconsOptions dev_build=yes"

    # build with dev_build=yes debug_symbols=no
    format-eval scons "$sconsOptions dev_build=yes debug_symbols=no"
}
