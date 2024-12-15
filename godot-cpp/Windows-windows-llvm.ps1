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

function Prepare {
    Figlet "Prepare"
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|obj"
    
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
    
    $llvmPath = 'C:\Program Files\LLVM\bin\'
    H3 "Prepend `$env:path with $llvmPath"
    $savePath = $env:Path
    $env:Path = "$llvmPath;" + $env:Path
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
    # SCons Build
    Set-Location "$buildRoot\test"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    BuildSCons -v @("use_llvm=yes") -t $targets
    
    #Restore Path
    $env:Path = $savePath
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    EraseFiles -f "libgdexample" -e "dll"
    
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