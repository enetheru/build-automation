#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c) {
    return
}

function Prepare {
    Figlet "Prepare"
    
    H4 "Adding LLVM to PATH"
    $llvmPath = 'C:\Program Files\LLVM\bin\'
    $env:Path = "$llvmPath;" + $env:Path
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "example|editor_plugin_registration" "o|obj|os"
    EraseFiles "libgodot-cpp.windows" "a"
    EraseFiles "libgdexample.windows" "dll"
    
    PrepareScons
    
    $toolChain = "$root\toolchains\w64-llvm.cmake"
    
    # FIXME, force re-generating the bindings
    
    [array]$cmakeVars = @(
        "-GNinja",
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
    EraseFiles "libgdexample" "dll"
    EraseFiles "libgodot-cpp" "lib"
    
    ## SCons Build
    Set-Location "$buildRoot\test"
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    BuildSCons -v @("use_llvm=yes") -t $targets
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles "libgdexample" "dll"
    EraseFiles "libgodot-cpp" "lib"
    
    ## CMake Build
    Set-Location "$buildRoot\cmake-build"
    [array]$targets = @(
        "godot-cpp.test.template_debug",
        "godot-cpp.test.template_release",
        "godot-cpp.test.editor")
    BuildCMake -t $targets

    # Report Results
    $statArray | Format-Table
}

function Test {
    TestCommon
}