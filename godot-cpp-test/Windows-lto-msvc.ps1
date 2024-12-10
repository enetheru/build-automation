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

$godotcppGitURL = "C:/Godot/src/godot-cpp"
$godotcppGitBranch = "lto"

function Prepare {
    PrepareCommon


    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
}

function Build {
    H1 "CMake Build"
    $doFresh = ($fresh) ? "--fresh" : $null
    
    $doVerbose = ($verbose) ? "--verbose" : $null
    $MSBuildOptions = "/nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""
    
    [array]$cmakeVars = @(
                "-DGODOTCPP_GIT_URL=$godotcppGitURL",
                "-DGODOTCPP_GIT_BRANCH=$godotcppGitBranch",
                "-DGODOT_LTO=ON"
    )

    Set-Location $buildDir
    foreach( $target in @("template_debug", "template_release", "editor") ){
        Format-Eval "cmake $doFresh .. -DTEST_TARGET=$target $($cmakeVars -join ' ')"
        Format-Eval "cmake --build . $doVerbose --config RelWithDebInfo -- $MSBuildOptions"
    }
}
