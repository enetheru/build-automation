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

    $doVerbose = ($verbose) ? "verbose=yes" : $null

    foreach( $target in ("template_debug", "template_release", "editor") ) {
        H2 "Building $target"
        Format-Eval scons "$doVerbose target=$target dev_build=yes"
    }

    H4 "Changing directory to $buildRoot/test"
    Set-Location "$buildRoot/test"

    foreach( $target in ("template_debug", "template_release", "editor") ) {
        H3 "Building integration test using target=$target"
        Format-Eval scons "$doVerbose target=$target dev_build=yes"
    }
}

function Test {
    TestCommon
}