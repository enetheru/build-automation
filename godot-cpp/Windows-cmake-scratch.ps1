#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    $envRun = "pwsh"
    $envActions = "Windows-actions.ps1"
    $envClean = "CleanLog-Default"
    Write-Output @"

    envRun        = $envRun
    envActions    = $envActions
    envClean      = $envClean
"@
    return
}

$script:buildDir = ''

function Prepare {
    PrepareCommon
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    $script:buildDir = "$buildRoot/cmake-build-default"
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir

    Format-Eval cmake "$doFresh .. -DGODOT_ENABLE_TESTING=ON"
}

function Build {
    H1 "CMake Build"
    $doVerbose = ($verbose -eq $true) ? "--verbose" : $null
    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"

    Set-Location $buildDir
    Format-Eval cmake "--build . $doVerbose -t godot-cpp-test --config RelWithDebInfo -- $MSBuildOptions"
}
