#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ){
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
    Set-Location "$buildRoot/test"

    Format-Command "scons verbose=yes platform=android target=template_release arch=x86_64"
    scons verbose=yes platform=android target=template_release arch=x86_64
}

function Test {
    H4 "TODO Testing"
}