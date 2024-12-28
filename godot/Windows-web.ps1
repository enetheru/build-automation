#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    H4 "Using Default env Settings"
    return
}

# Documentation specifies that for godotengine 4.3 the Emscripten version is 3.1.39. but that fails.
# the github CI uses 3.1.64, so thats what we will use.
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

    # According to the github CI, it builds on ubuntu for both threads and no threads.
    # And has a set of flags that it uses and only builds for template_release
    # threads=no/yes
    # warnings=extra werror=yes debug_symbols=no use_closure_compiler=yes strict_checks=yes
    # which means that it's never tested regularly on windows. Pretty shit if you ask me.
    
    [array]$targets = @(
        "template_debug",
        "template_release",
        "editor")
    [array]$sconsVars = @(
        "platform=web",
        "dlink_enabled=yes",
        "threads=no",
        "warnings=extra",
        "werror=yes",
        "debug_symbols=no", 
        # "use_closure_compiler=yes", # Fails to run command due to invalid quoting Error listed below #1
        "strict_checks=yes")
    BuildSCons -v $sconsVars -t $targets
    
    # TODO Report Build Artifact sizes
    
    # Report Results
    $statArray | Format-Table
}

#1 C:\Program Files\nodejs\node.EXE C:\emsdk\upstream\emscripten\node_modules\.bin\google-closure-compiler --compilation_level ADVANCED_OPTIMIZATIONS --externs C:\build\godot\Windows-web\platform\web\js\engine\engine.externs.js --js C:\build\godot\Windows-web\platform\web\js\engine\features.js --js C:\build\godot\Windows-web\platform\web\js\engine\preloader.js --js C:\build\godot\Windows-web\platform\web\js\engine\config.js --js C:\build\godot\Windows-web\platform\web\js\engine\engine.js --js_output_file C:\build\godot\Windows-web\bin\godot.web.template_debug.wasm32.nothreads.dlink.engine.js
# 'C:\Program' is not recognized as an internal or external command,
# operable program or batch file.
