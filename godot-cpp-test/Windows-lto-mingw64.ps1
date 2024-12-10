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

$godotcppGitURL = "C:/Godot/src/godot-cpp"
$godotcppGitBranch = "lto"

$script:buildDir = "$buildRoot/cmake-build"

function Prepare {
    H1 "CMake Configure"
    PrepareCommon
    
    $doFresh = ($fresh) ? "--fresh" : $null
    
    $toolChain = "$root\toolchains\w64-mingw-w64.cmake"
    
    [array]$configVars = @(
        "-G'MinGW Makefiles'",
        "-DGODOTCPP_GIT_URL=$godotcppGitURL",
        "-DGODOTCPP_GIT_BRANCH=$godotcppGitBranch",
#        "-DGODOT_LTO=ON",
        "--toolchain $toolchain"
    )
    
    H3 "Prepend `$env:path with C:\mingw64\bin"
    $env:Path = 'C:\mingw64\bin;' + $env:Path
    
    foreach( $target in @("template_debug", "template_release", "editor") ) {
        if( -Not (Test-Path -Path "$buildDir-$target" -PathType Container) ) {
            H4 "Creating $buildDir-$target"
            New-Item -Path "$buildDir-$target" -ItemType Directory -Force | Out-Null
        }
        Set-Location "$buildDir-$target"
        Format-Eval "cmake -j$jobs $doFresh .. -DTEST_TARGET=$target $($configVars -join ' ')"
    }
}

function Build {
    $doVerbose = ($verbose) ? "--verbose" : $null
    
    foreach( $target in @("template_debug", "template_release", "editor") ){
        if( -Not (Test-Path -Path "$buildDir-$target" -PathType Container) ) {
            Write-Error "build Directory missing $buildDir-$target"
        }
        Set-Location "$buildDir-$target"
        
        H1 "CMake Build"
        Format-Eval "cmake --build . -j$jobs $doVerbose --config RelWithDebInfo"
    }
}
