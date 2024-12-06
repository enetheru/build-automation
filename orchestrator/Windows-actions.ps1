#!/usr/bin/env pwsh
#Requires -Version 7.4

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$statsSchema = @{
    fetch   = ($fetch -eq $true) ? "Fail" : "-"
    prepare = ($prepare -eq $true) ? "Fail" : "-"
    build   = ($build -eq $true) ? "Fail" : "-"
    test    = ($test -eq $true) ? "Fail" : "-"
}
$stats = [PSCustomObject]$statsSchema

function PrintStats {
    @"
(`$statistics).fetch    = "$(($stats).fetch)"
(`$statistics).prepare  = "$(($stats).prepare)"
(`$statistics).build    = "$(($stats).build)"
(`$statistics).test     = "$(($stats).test)"
"@
}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    PrintStats
    Start-Sleep -Seconds 1
}

. "$root/share/format.ps1"

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$config = Split-Path -Path $script -LeafBase

H2 "Build '$target' on '$platform' using '$config'"
Write-Output @"
  envActions  = $thisScript
  buildScript = $script

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test

  fresh build = $fresh
  log append  = $append
"@

# Main Variables
[string]$godot = "C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr = "C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

Write-Output @"

  godot.editor           = $godot
  godot.template_release = $godot_tr
"@

# [System.Uri]$sourceOrigin = "https://github.com/CraterCrash/godot-orchestrator.git"
[System.Uri]$gitUrl = "C:\Godot\extensions\godot-orchestrator"
#[string]$sourceBranch = "2.0"
#[string]$sourceHash = "e4ef00d9ed8ad67b876f0e6223b03bd7b2fc3d93" #2.0.4.stable
[string]$gitBranch = "2.1-modernise"
#[string]$sourceHash = "d091f26c28de2b7108c9890f2b97b901795fa151" # 2.1.2.stable

Write-Output @"

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch
"@

# Get the target root from this script location
$targetRoot = $thisScript  | split-path -parent
$buildRoot = "$targetRoot\$config"

Write-Output @"

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  buildRoot   = $buildRoot
"@

Set-Location "$targetRoot"

function FetchSubmodules {
    H3 "Update Submodules"
    
    H4 "godot-cpp"
    $moduleDir = "$buildRoot/extern/godot-cpp"
    
    if( -Not (Test-Path "$moduleDir/*") ) {
        Format-Eval "git submodule update --init --remote `"$moduleDir`""
    }
    
    Set-Location "$moduleDir"
    
    if( -Not (git remote -v | Select-String -Pattern "local" -Quiet) ) {
        Format-Eval "git remote add local C:\godot\src\godot-cpp"
    }
    
    if( (git fetch --dry-run 2>&1) ){
        Format-Eval "git fetch --all"
    }
    
    $modBranch="4.3-modernise"
    if( -Not (git branch --show-current | Select-String -Pattern "$modBranch" -Quiet) ) {
        Format-Eval "git checkout `"local/$modBranch`" --track"
    }
    
    # Fetch any changes and reset to latest
    H4 "Status"
    git status
}

# Some steps are identical.
function PrepareCommon {
    Set-Location "$buildRoot"

    # Clean up key artifacts to trigger rebuild
#    '(orchestration.cpp|orchestrator.windows)'
    [array]$artifacts = @($(rg -u --files "$buildRoot" `
        | rg "(memory|example).*?o(bj)?$"))

    $artifacts += @($(rg -u --files "$buildRoot" `
        | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))

    if( $artifacts.Length -gt 0 ) {
        H3 "Removing key Artifacts"
        $artifacts | Sort-Object | Get-Unique | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }

#    # SCons - Remove generated source files if exists.
#    if( Test-Path "$buildRoot\gen" -PathType Container ) {
#        H4 "Removing Generated Files"
#        Remove-Item -LiteralPath "$buildRoot\gen" -Force -Recurse
#    }
}

function TestCommon {
#    Write-Output "" >> "$targetRoot\summary.log"
#    H4 "$config" >> "$targetRoot\summary.log"

    $projectDir = "$buildRoot\project"

    if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        & {
            $PSNativeCommandUseErrorActionPreference = $false
            &$godot -e --path "$projectDir" --quit --headless *> $null
            # Godot spawns and detaches another process, making this harder than it needs to be.
            # FIXME find a way to get the actual process ID that I want to wait on.
            while( Get-Process | Where-Object -Property "ProcessName" -Match "godot" ) {
                #This is a slightly better fix than before, but I still want to get the specific process.
                Start-Sleep -Seconds 1
            }
        }
        if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
            Write-Error "Failed to create .godot folder" >> "$targetRoot\summary.log"
        }
    }
    
    H4 "Run the test project"
    $result = ("ERROR")
    &$godot --path "$projectDir" --quit --headless 2>&1 | Out-String | Tee-Object -Variable result
    
    while( Get-Process | Where-Object -Property "ProcessName" -Match "godot" ) {
        #This is a slightly better fix than before, but I still want to get the specific process.
        Start-Sleep -Seconds 1
    }

    Write-Output $result
    if( $result -Match "ERROR: GDExtension dynamic library not found" ) {
        Write-Error "Test Failure"
        Write-Error "Fail"
    } else {
        Write-Output "Test Succeded"
        Write-Output "OK"
    }
}

H3 "Processing - $config"

# Source generic actions, and then override.
. "$root\share\build-actions.ps1"
. "$targetRoot\$script"

if( $fetch      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Fetch"
    Fetch
    ($stats).fetch = "OK"
}

if( $prepare  -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Prepare"
    Prepare
    ($stats).prepare = "OK"
}

if( $build      -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Build"
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    Build
    $timer.Stop();
    H3 "Build Duration: $($timer.Elapsed)"
    ($stats).build = "OK"
}

if( $test       -eq $true ) {
    $Host.UI.RawUI.WindowTitle = "$target | $config | Test"
    Test | Tee-Object -Variable result
    ($stats).test = ($result | Select-Object -Last 1)
}

PrintStats

Start-Sleep 1