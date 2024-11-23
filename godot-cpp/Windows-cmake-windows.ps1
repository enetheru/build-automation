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
    H1 "CMake Build"

    H4 "Creating build Dir"
    $buildDir = "$buildRoot\cmake-build"
    New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    Set-Location $buildDir

    H4 "CMake Configure"
    if( $fresh ) {
        $doFresh = '--fresh'
    } else {
        $doFresh = ''
    }

    H3 "Configurin godot-cpp"
    Format-Command "cmake $doFresh ..\ -DTEST_TARGET=template_release"
    cmake $doFresh ..\ -DTEST_TARGET=template_release

    $vsExtraOptions = "/nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""

    H3 "Building godot-cpp::template_debug"
    Format-Command "cmake --build . -j 12 --verbose -t template_debug --config Release -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t template_debug --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H3 "Building godot-cpp::template_release"
    Format-Command "cmake --build . -j 12 --verbose -t template_release --config Release -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t template_release --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H3 "Building godot-cpp::editor"
    Format-Command "cmake --build . -j 12 --verbose -t editor --config Release -- $vsExtraOptions"
    cmake --build . -j 12 --verbose -t editor --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"

    H4 "Building godot-cpp-test"
    Format-Command "cmake --build . -j 12 --verbose -t godot-cpp-test --config Release -- /nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""
    cmake --build . -j 12 --verbose -t godot-cpp-test --config Release -- /nologo /v:m /clp:"ShowCommandLine;ForceNoAlign"
}

function Test {
    TestCommon
}