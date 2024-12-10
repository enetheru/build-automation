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
    
    $llvmPath = 'C:\Program Files\LLVM\bin\'
    H3 "Prepend `$env:path with $llvmPath"
    $env:Path = "$llvmPath;" + $env:Path
    
    $buildDir = "$buildRoot/test"
    H4 "Changing directory to $buildDir"
    Set-Location "$buildDir"
    foreach( $target in @("template_debug", "template_release", "editor") ){
        H2 "$target"
        H1 "Scons Build"
        Format-Eval "scons -j $jobs use_llvm=yes target=$target"
    }
}

function Test {
    TestCommon
}