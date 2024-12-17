#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c -eq $true ) {
    $mingwPath = 'C:\mingw64\bin'
    H3 "Prepend `$env:path with $mingwPath"
    $env:Path = "$mingwPath;" + $env:Path
    
#    function CleanLog {
#        $erase = "==+-?"
#
#        ## Strip the build paths from any string.
#        $erase += "|$([Regex]::Escape($targetRoot))"
#
#        # Strip the mingw path from strings
#        # TODO I'm not sure I want to erase this.
##        $erase += "|$([Regex]::Escape($mingwPath))"
#
#        # [100%] Linking CXX shared library
#        $erase += "|$([Regex]::Escape("[100%]")) Linking CXX shared library.*"
#
#        # scons: `bin\libgodot-cpp.windows.editor.x86_64.a' is up to date.
#        $erase += "|scons:.*is up to date\."
#
#        $lineMatch = '== (Config|Target)|example\.o|libgdexample.*\.dll|libgodot-cpp.*\.a'
#
#        $joins = '-o|(Target|Config):|Removing'
#
#        $prevLine = $null
#        Get-Content "$args" | Where-Object {    # Match only specific lines
#            $_ -Match "$lineMatch"
#        } | ForEach-Object {  # quick cleanup, trim, and split
#            ($_ -creplace "$erase", "").Trim() -cSplit '\s+'
#        } | ForEach-Object {  # Re-Join Lines
#            if( $prevLine ) { "$prevLine $_"; $prevLine = $null }
#            elseif( $_ -cmatch "^$joins" ) { $prevLine = "$_" }
#            else { $_ }
#        } | ForEach-Object {  # Embellish to make easier to read
#            $_  -creplace '^(Config)',"`n## `$1" `
#                -creplace '^(Target)','## $1' `
#                -creplace '^(g[+]{2})',"`n`$1" `
#                -creplace "^(.*[^d=]c[+]{2})","`n`$1"
#        } | Where-Object { # Second Skip
#            $_ -notmatch '^Remov|^$'
#        }
#    }
    return
}

function Prepare {
    Figlet "Prepare"
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|d|obj"
    EraseFiles "libgodot-cpp" "a"
    
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
    Set-Location "$buildRoot\cmake-build"
    [array]$targets = @(
        "godot-cpp.test.template_debug",
        "godot-cpp.test.template_release",
        "godot-cpp.test.editor")
    BuildCMake -t $targets

    # Report Results
    $statArray | Format-Table
}