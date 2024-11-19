#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    [switch] $freshBuild, # defaults to false
    [switch] $testBuild, # defaults to false
    [switch] $appendTrace # defaults to false
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Main Variables
[string]$godot = "C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr = "C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

[string]$root = "C:\build\godot-cpp-template"
[System.Uri]$sourceOrigin = "http://github.com/enetheru/godot-cpp-template.git"
$sourceBranch = "cmake"

# Automtion Begin
Set-Location $root

function TargetPrep {
    param(
        [Parameter( Mandatory = $true )] [string]$hostTarget,
        [Parameter( Mandatory = $true )] [System.Uri]$sourceOrigin,
        $sourceBranch
    )

    Set-Location $root

    [string]$sourceDest = "$root/$hostTarget"

    # Clone the repository
    if( -Not (Test-Path -Path $sourceDest -PathType Container) ) {
        git clone (${sourceBranch}?.Insert(0, "-b")) "$sourceOrigin" "$sourceDest"
    }

    # Change working directory
    Set-Location $sourceDest

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if( $sourceBranch ) {
        git checkout $sourceBranch
    }

    # Submodules godot-cpp needs its updating to test modernise branch
    if( -Not (Test-Path godot-cpp\*) ) {
        git submodule set-url -- godot-cpp https://github.com/enetheru/godot-cpp.git
        git submodule set-branch -b modernise godot-cpp
        git submodule sync
        git submodule update --init --recursive --remote
    }

    # Remove key build artifacts before re-build
    # Turn off failure on Non-Zero exit code for ripgrep finding no results
    $PSNativeCommandUseErrorActionPreference = $false
    rg -u --files | rg "\.(dll|so|wasm|dylib|lib)$" | ForEach-Object { Remove-Item $_ }
    rg -u --files | rg "register_types.*?\.(o|obj|so)$" | ForEach-Object { Remove-Item $_ }
    #Turn back on exit failures.
    $PSNativeCommandUseErrorActionPreference = $true
}

function TargetBuild {
    param(
        $msys2Env,
        $hostTarget
    )
    $traceLog = "$root/$hostTarget.txt"
    $buildRoot = "$root/$hostTarget"
    $msys2_shell = "C:/msys64/msys2_shell.cmd -$msys2Env -defterm -no-start -where $buildRoot"

    #unix shell script, and shell varibles.
    $buildScript = "/c/build/godot-cpp-template/$hostTarget.sh"
    $vars = "GODOT=/c/build/godot/msvc.master/bin/godot.windows.editor.x86_64.exe"
    $vars += " GODOT_TR=/c/build/godot/msvc.master/bin/godot.windows.template_release.x86_64.exe"
    $vars += " BUILD_ROOT=/c/build/godot-cpp-template/$hostTarget"
    $vars += " FRESH=$($freshBuild ? "--fresh" : $null)"
    $vars += " TEST=$($testBuild ? "1" : 0)"

    "cmd /c $msys2_shell -c `"$vars $buildScript`" 2>&1" `
        | pwsh -nop -Command - `
        | Tee-Object -FilePath $traceLog
}

# Build using msys2
foreach( $msys2Env in @('ucrt64'; 'mingw64'; 'mingw32'; 'clang64'; 'clang32'; 'clangarm64') ) {
    $buildScripts = (rg --max-depth 1 --files | rg "msys2-$msys2env.+\.sh$")
    foreach( $buildScript in $buildScripts ) {
        $hostTarget = ([System.IO.Path]::GetFileNameWithoutExtension( $buildScript ))
        Set-PSDebug -Trace 1

        TargetPrep -hostTarget $hostTarget -sourceOrigin $sourceOrigin -sourceBranch $sourceBranch
        TargetBuild -msys2Env $msys2Env -hostTarget $hostTarget

        Set-PSDebug -Off
        Set-Location $root
    }
}

# When running from the play button in clion I get an exception after the script finishes
#   An error has occurred that was not properly handled. Additional information is shown below.
#   The PowerShell process will exit.
#   Unhandled exception. System.Management.Automation.PipelineStoppedException: The pipeline has been stopped.
# This can be stopped by just sleeping for a second.
Start-Sleep -Seconds 1