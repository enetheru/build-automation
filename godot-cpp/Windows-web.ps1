#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c -eq $true ) {
    H4 "Using Default env Settings"
    return
}

$script:emsdk = "C:\emsdk"

function Prepare {
    Figlet "Prepare"
    
    UpdateEmscripten
    
    H3 "Activate EmSDK"
    Format-Eval $emsdk\emsdk.ps1 activate latest
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|obj"
    
    PrepareScons -v @("platform=web")
    
    $toolchain = "$emsdk\upstream\emscripten\cmake\Modules\Platform\Emscripten.cmake"
    # FIXME, investigate the rest of the emcmake pyhton script for any other options.
    
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
    
    # TODO Erase previous artifacts
#    Set-Location "$buildRoot"
#    EraseFiles -f "libgdexample" -e "dll"
    
    #SCons Build
    Set-Location "$buildRoot\test"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    BuildSCons -v @("platform=web") -t $targets
    
    # TODO Erase previous artifacts
    #    Set-Location "$buildRoot"
    #    EraseFiles -f "libgdexample" -e "dll"
    
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