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
    # https://stackoverflow.com/questions/24347758/remove-alias-in-script
    Remove-Item 'Alias:\Fetch' -Force
    Fetch #Original Fetch
    FetchSubmodules
}
New-Alias -Name 'Fetch' -Value 'MyFetch' -Scope Global

function Prepare {
    H1 "Prepare"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    PrepareCommon

    $script:buildDir = "$buildRoot/cmake-build"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    H3 "CMake Configure"
    $toolchain = "C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake"
    [array]$cmakeVars = "-GNinja"
    $cmakeVars += "-DCMAKE_BUILD_TYPE=Release"
    $cmakeVars += "-DANDROID_PLATFORM=android-29"
    $cmakeVars += "-DANDROID_ABI=x86_64"
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
