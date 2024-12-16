#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [Alias( "c" )] [switch] $config )
if( $config -eq $true ) {
    # [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
    [System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"
    if( $gitBranch -eq "" ){ $gitBranch = "master" }
    
    # This function is called when the build is completed to whittle down the
    # build log to something usable.
    function CleanLog {
        H3 "Cleaning $args"
        # Clean the logs
        # it goes like this, for each line that matches the pattern.
        # split each line along spaces.
        # [repeated per type of construct] re-join lines that match a set of tags
        # the remove the compiler defaults, since CMake adds so many.
        
        $matchPattern = '^lib|^link|memory|Lib\.exe|link\.exe|  󰞷'
        [array]$compilerDefaults = (
        "fp:precise",
        "Gd", "GR", "GS",
        "Zc:forScope", "Zc:wchar_t",
        "DYNAMICBASE", "NXCOMPAT", "SUBSYSTEM:CONSOLE", "TLBID:1",
        "errorReport:queue", "ERRORREPORT:QUEUE", "EHsc",
        "diagnostics:column", "INCREMENTAL", "NOLOGO", "nologo")
        & {
            $PSNativeCommandUseErrorActionPreference = $false
            rg -M2048 $matchPattern "$args" `
            | sed -E 's/ +/\n/g' `
            | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' `
            | sed -E ':a;$!N;s/(Program|Microsoft|Visual|vcxproj|->)\n/\1 /;ta;P;D' `
            | sed -E ':a;$!N;s/(\.\.\.|omitted|end|of|long)\n/\1 /;ta;P;D' `
            | sed -E "/^\/($($compilerDefaults -Join '|'))$/d"
        }
    }
    return
}

# PowerShell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$stats = [PSCustomObject]@{
    fetch   = ($fetch -eq $true) ? "Fail" : "-"
    prepare = ($prepare -eq $true) ? "Fail" : "-"
    build   = ($build -eq $true) ? "Fail" : "-"
    test    = ($test -eq $true) ? "Fail" : "-"
}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    Finalise $stats
    Start-Sleep -Seconds 1
}

. "$root/share/format.ps1"

# Setup our variables

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$targetRoot = $thisScript  | split-path -parent

$config = Split-Path -Path $script -LeafBase

$buildRoot = "$targetRoot\$config"

# [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
[System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"

[string]$godot = "C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr = "C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

#### Write Summary ####
SummariseConfig

# Add custom things to Summary
Write-Output @"
  godot.editor           = $godot
  godot.template_release = $godot_tr
"@

Set-Location "$targetRoot"

# Host Platform Values and Functions
. "$root\share\build-actions.ps1"

# Prepare with SCons
# In the case of godot-cpp we can generate the bindings without building the library
# It will auto generate the bindings, or we can force it if fresh is enabled.
function PrepareScons {
    param(
        [Alias( "v" )] [array] $vars = @()
    )
    # requires SConstruct file existing in the current directory.
    if( -Not (Test-Path "SConstruct" -PathType Leaf) ) {
        Write-Error "PrepareScons: Missing '$(Get-Location)\SConstruct'"
        Return 1
    }
    
    Figlet -f "small" "SCons Prepare"
    
    # SCons - Remove generated source files if exists.
    $doFresh = ($fresh -eq $true) ? "generate_bindings=yes" : $null
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    $buildVars = @( "$doVerbose", "$doFresh") + $vars
    
    # Is effected by three variables
    # target arch cpu width, either 32 or 64, FIXME default unknown, I guess host architecture?
    # generate_template_get_node, default is 'yes'.
    # precision, single/double, default is 'single'.
    Format-Eval "scons $($buildVars -Join ' ') build_library=no"
}

# SCons - Remove generated source files if exists.
function EraseGen {
    
    if( Test-Path "$buildRoot\gen" -PathType Container ) {
        H4 "Removing Generated Files"
        Remove-Item -LiteralPath "$buildRoot\gen" -Force -Recurse
    }
}

function TestCommon {
    Write-Output "" >> "$targetRoot\summary.log"
    H4 "$config" >> "$targetRoot\summary.log"

    if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        Format-Command "$godot -e --path `"$buildRoot\test\project`" --quit --headless"
        & $godot -e --path "$buildRoot\test\project" --quit --headless 2>&1 | Tee-Object -Variable result
        Start-Sleep -Seconds 1

        if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
            Write-Output "Failed to create .godot folder" >> "$targetRoot\summary.log"
            return 1
        }
    } else {
        H4 "The .godot folder has already been generated."
    }

    H4 "Run the test project"
    Format-Command "$godot_tr --path `"$buildRoot\test\project\`" --quit --headless`n"
    & $godot_tr --path "$buildRoot\test\project\" --quit --headless | Tee-Object -Variable result
    @($result.split( "`r`n" ) | Where-Object { $_ -Match "FINI|PASS|FAIL|Godot" }) >> "$targetRoot\summary.log"
}

# Per config Overrides and functions
. "$targetRoot\$script"

H3 "$config - Processing"

if( $fetch -eq $true ) {
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare -eq $true ) {
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "$config - Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test -eq $true ) {
    $result = ("unknown")
    Test
    ($stats).test = "OK"
}

H2 "$config - Completed"

Finalise
Start-Sleep 1
