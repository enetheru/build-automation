#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c -eq $true ) {
    $mingwPath = 'C:\mingw64\bin'
    H3 "Prepend `$env:path with $mingwPath"
    $env:Path = "$mingwPath;" + $env:Path
    return
}

function Prepare {
    Figlet "Prepare"
    

    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|obj"
    
    PrepareScons
    
    $toolChain = "$root\toolchains\w64-mingw-w64.cmake"
    
    [array]$cmakeVars = @(
        "-G'MinGW Makefiles'",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGODOT_ENABLE_TESTING=YES",
        "--toolchain $toolchain"
    )
    PrepareCMake -v $cmakeVars
}

function Build {
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
    Set-Location "$buildRoot\test"
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    BuildSCons -v @("use_mingw=yes") -t $targets
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
    ## CMake Build
    Set-Location "$buildDir\cmake-build"
    [array]$targets = @(
        "godot-cpp.test.template_debug",
        "godot-cpp.test.template_release",
        "godot-cpp.test.editor")
    BuildCMake -t $targets

    # Report Results
    $statArray | Format-Table
}