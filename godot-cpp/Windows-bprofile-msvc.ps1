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

$script:buildDir = "$buildRoot/cmake-build"

$gitBranch = "build_profile"

function Prepare {
    H1 "Prepare"
    
    
    EraseFiles "editor_plugin_registration" "o|obj"
    
    H3 "CMake Configure"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null

    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }

    Set-Location $buildDir
    H1 "CMake Configure"

    [array]$cmakeVars = $null
    $cmakeVars += "-DGODOT_ENABLE_TESTING=YES"
    $cmakeVars += "-DGODOT_BUILD_PROFILE='..\test\build_profile.json'"
    
    Format-Eval "cmake $doFresh .. $($cmakeVars -Join ' ')"
}

function Build {
    [array]$statArray = @()
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
    ## SCons Build
    Set-Location "$buildRoot\test"
    BuildSCons -v @("build_profile=build_profile.json")
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
    ## CMake Build
    Set-Location "$buildDir"
    BuildCMake -v @("--config Release")
    
    # Report Results
    $statArray | Format-Table
}
