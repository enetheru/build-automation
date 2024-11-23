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

    H4 "Changing directory to $buildRoot"
    Set-Location "$buildRoot"

    H3 "Building godot-cpp template_debug"
    Format-Command "scons verbose=yes dev_build=yes target=template_debug"
    scons verbose=yes dev_build=yes target=template_debug

    H3 "Building godot-cpp template_release"
    Format-Command "scons verbose=yes dev_build=yes target=template_release"
    scons verbose=yes dev_build=yes target=template_release

    H3 "Building godot-cpp editor"
    Format-Command "scons verbose=yes dev_build=yes target=editor"
    scons verbose=yes dev_build=yes target=editor

    H3 "Building test extension"
    H4 "Changing directory to $buildRoot/test"
    Set-Location "$buildRoot/test"

    Format-Command "scons verbose=yes dev_build=yes target=template_release"
    scons verbose=yes dev_build=yes target=template_release
}

function Test {
    TestCommon
}