#!/usr/bin/env pwsh
#Requires -Version 7.4

[CmdletBinding(PositionalBinding=$false)]
param(
    [string]$prefix='w64',
    [switch]$help, [switch]$h,
    [Parameter(ValueFromRemainingArguments=$true)]$args
)
"Config Prefix: '$prefix'"
"Config Search Patterns: '$args'"

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


# Help and prevent direct call.
if( $h -or $args -match "--help|/\?" ){ $help = $true  }
if( $MyInvocation.ScriptLineNumber -eq 1 -Or $help){
    Write-Output "`$args = '$args'"
    Write-Error "This script cannot be run directly."
}

# Main Variables
[string]$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

# Process varargs for build configs.
if( $args ){
    $patterns = $args -split '\s+' -join '|'
    [string]$pattern = "^$prefix-(.*?)($patterns)(.*?)\.(ps1|sh)$"
    "Search command = rg -u --files --max-depth 1 | rg $pattern"
    [array]$buildConfigs = rg -u --files --max-depth 1 | rg $pattern `
        | ForEach-Object { Split-Path -LeafBase $_ }
} else {
    "Searching in: $(Get-Location)"
    [array]$buildConfigs = rg --files --max-depth 1 `
        | rg "$prefix(.*?)-(cmake|scons)-(.*?).(ps1|sh)$" `
        | ForEach-Object { Split-Path -LeafBase $_ }
    "Found: '$buildConfigs'"
}

# Quit if there are no configs.
if( -Not ($buildConfigs -is [array] -And $buildConfigs.count -gt 0) ) {
    if( $args ){ Write-Error "No configs found for: {$args}"
    } else { Write-Error "No Configs found in folder."  }
    exit 1
}

"== Build Configurations =="
$buildConfigs | Format-List -Property Name

# Helper Function for changing windwos paths to msys2 paths.
Function Win2Unix {
    [CmdletBinding()]
    Param( [Parameter(ValueFromPipeline)] $Name )
    process { $Name -replace '\\','/' -replace ':','' -replace '^C','/c'  }
}


function SourcePrep {
    param(
        [Parameter(Mandatory=$true)] [string]$buildRoot,
        [Parameter(Mandatory=$true)] [System.Uri]$sourceOrigin,
        $sourceBranch
    )
    "== Source Code =="
    "Git URL: $sourceOrigin"
    "Git Branch: $sourceBranch"
    "Source Dest: $buildRoot"
    Set-Location $root

    # Clone the repository
    if (-Not (Test-Path -Path $buildRoot -PathType Container))
    {
        git clone (${sourceBranch}?.Insert(0, "-b")) "$sourceOrigin" "$buildRoot"
    }

    # Change working directory
    Set-Location $buildRoot

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if ($sourceBranch)
    {
        git checkout $sourceBranch
    }

    #TODO fix when the tree diverges and needs to be clobbered.
}


function w64Build {
    param(
        [Parameter(Mandatory=$true)][string]$buildRoot
    )
    $hostTarget = Split-Path -LeafBase $buildRoot
    #Script and Log variables
    $buildScript="$root\$hostTarget.ps1"
    $rawLog="$root/logs-raw/$hostTarget.txt"
    $cleanLog="$root/logs-clean/$hostTarget.txt"

    #Build Variables
    $fresh = ($freshBuild) ? "`"--fresh`"" : "`$null"
    $test = ($noTestBuild) ? "`$false" : "`$true"

    # This script will be source of the exported log, and sources the build script.
    @"
#Requires -Version 7.4
Set-StrictMode -Version Latest
`$ErrorActionPreference = "Stop"
`$PSNativeCommandUseErrorActionPreference = `$true

Set-PSDebug -Trace 1

`$root="$root"
`$godot="$godot"
`$godot_tr="$godot_tr"

`$hostTarget="$hostTarget"
`$buildRoot="$buildRoot"
`$fresh=$fresh
`$test=$test

. $buildScript

Set-PSDebug -Off

"@ | pwsh -nop -WorkingDirectory $buildRoot -Command - | Tee-Object -FilePath $rawLog
    #TODO make the Tee-Object -Append option configurable.

    # Reset the working directory after we are done.
    Set-Location $root
}

function msys2Build {
    param(
        [Parameter(Mandatory=$true)] [string]$buildRoot,
        [string]$msys2Env = "clang64"
    )
    # Script and log variables
    $hostTarget = Split-Path -LeafBase $buildRoot
    $msys2_shell="C:/msys64/msys2_shell.cmd -$msys2Env -defterm -no-start -where $buildRoot"
    $rawLog="$root/logs-raw/$hostTarget.txt"
    $cleanLog="$root/logs-clean/$hostTarget.txt"

    #unix shell script, and shell varibles.
    $buildScript="$root/$hostTarget.sh" | Win2Unix
    $vars=@(
        "GODOT=$($godot | Win2Unix)"
        "GODOT_TR=$($godot_tr | Win2Unix)"
        "BUILD_ROOT=$($buildRoot | Win2Unix)"
        "FRESH=$($freshBuild ? "--fresh" : $null)"
        "TEST=$($noTestBuild ? '0' : '1')"
    )
    $vars

    "cmd /c $msys2_shell -c `"$vars $buildScript`" 2>&1" `
        | pwsh -nop -Command - | Tee-Object -FilePath $rawLog

    # Reset the working directory after we are done.
    Set-Location $root
}

function Clean {
    param(
        [Parameter(Mandatory=$true)][string]$buildRoot,
        [Parameter(Mandatory=$true)][string]$matchPattern
    )
    $hostTarget = Split-Path -LeafBase $buildRoot
    $rawLog="$root/logs-raw/$hostTarget.txt"
    $cleanLog="$root/logs-clean/$hostTarget.txt"

    rg -M2048 $matchPattern $rawLog | sed -E 's/\s+/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > $cleanLog
}