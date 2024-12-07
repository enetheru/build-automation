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

$script:buildDir = ''

function Prepare {
    H1 "Prepare"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    PrepareCommon

    $toolChain = "$root\toolchains\w64-mingw-w64.cmake"

    $script:buildDir = "$buildRoot/cmake-build"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    H3 "Prepend `$env:path with C:\mingw64\bin"
    $env:Path = 'C:\mingw64\bin;' + $env:Path

    H3 "CMake Configure"
    $toolChain = "$root\toolchains\w64-mingw-w64.cmake"

    [array]$cmakeVars = "-G'MinGW Makefiles'"
    $cmakeVars += "-DCMAKE_BUILD_TYPE=Release"
    $cmakeVars += "--toolchain $toolchain"
    Format-Eval "cmake $doFresh .. $($cmakeVars -Join ' ')"
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null
    
    Set-Location $buildDir

    $cmakeVars = $null
    Format-Eval "cmake --build . $doVerbose $cmakeVars"
}

function Test {
    H1 "Test"
    TestCommon
}
