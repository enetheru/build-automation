#!/usr/bin/env pwsh
#Requires -Version 7.4

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

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

# [System.Uri]$sourceOrigin = "https://github.com/enetheru/godot-flatbuffers.git"
[System.Uri]$gitUrl = "C:\Godot\extensions\gdflatbuffers"
[string]$gitBranch = "4.4"

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

# Some steps are identical.
function PrepareCommon {
    Set-Location "$buildRoot"

    # Clean up key artifacts to trigger rebuild
    [array]$artifacts=@()
    & {
        $PSNativeCommandUseErrorActionPreference = $false
        $artifacts = @($(rg -u --files "$buildRoot" `
            | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))
    }

    if( $artifacts.Length -gt 0 ) {
        H3 "Removing key Artifacts"
        $artifacts | Sort-Object | Get-Unique | ForEach-Object {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
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
            while( Get-Process | Where-Object ProcessName -Match "godot" ) {
                #This is a slightly better fix than before, but I still want to get the specific process.
                Start-Sleep -Milliseconds 250
            }
        }
        if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
            Write-Error "Failed to create .godot folder" >> "$targetRoot\summary.log"
        }
    }
    H4 "Run the test project"
    $result = ("ERROR")
    &$godot --headless --path "$buildRoot\project\" -s test.gd 2>&1 `
        | Out-String `
        | Tee-Object -Variable result

    while( Get-Process | Where-Object ProcessName -Match "godot" ) {
        #This is a slightly better fix than before, but I still want to get the specific process.
        Start-Sleep -Milliseconds 250
    }

    $script:success = $false
    if($result -Split [Environment]::NewLine `
        | Select-String -Quiet -Pattern "LoadedExtensions.*gdflatbuffers"){
        Write-Output "OK"
    } else{
        Write-Error "Fail"
        
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
