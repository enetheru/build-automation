#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    $gitHash = "4.3"
    return
}

# According to documentation, godotengine - 4.3 requires Emscripten 3.1.39, but
# I get an error:
#   - Errors with TypeError: MOZ_TO_ME[node.type] is not a function
# Checking the GitHub CI it uses 3.1.64 as the version, why the discrepancy I
# don't know.
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
    
    Set-Location "$buildRoot"
    # Erase key files to trigger a re-build so we can capture the build commands.
    if( $fresh -eq $true ){
        H3 "Removing all files in $buildRoot\bin"
        Remove-Item -Recurse "bin\*"
    }
}

function Build {
    Figlet "Build"
    [array]$statArray = @()
    [ref]$statArrayRef = ([ref]$statArray)
    
    EmscriptenActivate "$emsdk" "$emsdkVersion"
    
    ## SCons Build
    Set-Location "$buildRoot"
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor"
        )
    [array]$sconsVars = @(
        "platform=web" )
    BuildSCons -v $sconsVars -t $targets
    
    # TODO Report Build Artifact sizes
    
    # Report Results
    $statArray | Format-Table
}
