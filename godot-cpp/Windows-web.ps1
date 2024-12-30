#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

$script:emsdk = "C:\emsdk"
$script:emsdkVersion = "3.1.64"

function FetchOverride {
    Figlet "Fetch"
    
    EmscriptenUpdate "$emsdk" "$emsdkVersion"
    
    # https://stackoverflow.com/questions/24347758/remove-alias-in-script
    Remove-Item 'Alias:\Fetch' -Force
    Fetch #Original Fetch
}
New-Alias -Name 'Fetch' -Value 'FetchOVerride' -Scope Global

function Prepare {
    Figlet "Prepare"
    
    EmscriptenActivate "$emsdk" "$emsdkVersion"
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
#    EraseFiles "editor_plugin_registration" "o|d|obj"
#    EraseFiles "libgodot-cpp.web" "a"
    
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
    
    EmscriptenActivate "$emsdk" "$emsdkVersion"
    
    # Erase previous artifacts
#    Set-Location "$buildRoot"
#    EraseFiles -f "libgdexample.web" -e "wasm"
    
    #SCons Build
    Set-Location "$buildRoot\test"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    [array]$sconsVars = @(
        "platform=web",
        "threads=no")
    BuildSCons -v $sconsVars -t $targets
    
    # Erase previous artifacts
#    Set-Location "$buildRoot"
#    EraseFiles -f "libgdexample.web" -e "wasm"
    
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