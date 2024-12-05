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

$toolchain = "C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake"
$options = "-DANDROID_PLATFORM=android-29 -DANDROID_ABI=x86_64"
$script:buildDir = ''

function Prepare {
    PrepareCommon

    $doFresh = ($fresh) ? "--fresh" : $null

    $script:buildDir = "$buildRoot/cmake-build-android"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    $cmakeVars = "-DGODOT_ENABLE_TESTING=YES -DTEST_TARGET=template_release --toolchain $toolchain"
    Format-Eval cmake "$doFresh .. $cmakeVars"
}

function Build {
    H1 "CMake Build"

    $doVerbose = ($verbose) ? "--verbose" : $null

    Set-Location $buildDir

    $cmakeVars = "--target godot-cpp-test --config Release"
    Format-Eval cmake "--build .. $doVerbose $cmakeVars"
}

function Test {
    H4 "TODO Testing"
}
