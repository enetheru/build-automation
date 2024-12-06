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

# Fetch Override
function MyFetch {
    Remove-Item 'Alias:\Fetch' -Force
    Fetch #Original Fetch
    FetchSubmodules
}
New-Alias -Name 'Fetch' -Value 'MyFetch' -Scope Global

function Prepare {
    H1 "Prepare"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    PrepareCommon

    # Create cmake-build directory
    $script:buildDir = "$buildRoot/cmake-build"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    H3 "CMake Configure"
    $toolChain = "$root\toolchains\w64-llvm.cmake"

    [array]$cmakeVars = "-GNinja"
    $cmakeVars += "--toolchain $toolchain"

    Format-Eval cmake "$doFresh .. $($cmakeVars -Join ' ')"
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null

    Set-Location $buildDir

    $cmakeVars = "--config Release"
    Format-Eval cmake "--build . $doVerbose $cmakeVars"
}

function Test {
    H1 "Test"
    TestCommon
}
