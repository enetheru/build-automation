#!/usr/bin/env pwsh
#Requires -Version 7.4

[CmdletBinding( PositionalBinding = $false )]
param(
    [Alias( "f" )] [switch] $fetch,
    [Alias( "p" )] [switch] $prepare,
    [Alias( "b" )] [switch] $build,
    [Alias( "t" )] [switch] $test,
    
    [Alias( "j" )] [int] $jobs = ([Environment]::ProcessorCount -1),

    [switch] $list,                 # show the list of scripts and exit
    [switch] $fresh,                # re-fresh the configuration
    [switch] $clean,                # clean the build directory
    [switch] $append,               # Append to the logs rather than clobber
    [string] $scriptFilter = ".*",  # Filter which scripts are used.

    [Parameter( Position = 0 )] [string] $target,       # Which target to use
    [Parameter( Position = 1 )] [string] $gitBranch,    # Which git branch to use

    [Parameter( ValueFromRemainingArguments = $true )]$passThrough #All remaining arguments
)

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$OutputEncoding = New-Object System.Text.UTF8Encoding
[console]::InputEncoding = $OutputEncoding
[console]::OutputEncoding = $OutputEncoding

$verbose = ($VerbosePreference -eq "Continue") ? $true : $false

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Start-Sleep -Seconds 1
}

$root = $PSScriptRoot

. ./share/format.ps1

function Syntax {
    Write-Output 'Syntax: ./build.sh -[fpbt] [-scriptFilter <regex>] <target>'
}

H1 "AutoBuild"
H2 "Options"

if( -Not ($fetch -Or $prepare -Or $build -Or $test) ) {
    $fetch = $true; $prepare = $true; $build = $true; $test = $true
}

Write-Output @"
  command     = '$($(Get-PSCallStack)[0].InvocationInfo.Line)'
  root        = $root

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test
  
  proc_count  = $jobs

  fresh build = $fresh
  log append  = $append
"@

if( $target -eq "" ) {
    Syntax
    Write-Error "Missing <target>"
}

Write-Output @"

  target      = $target
  branch      = $gitBranch
"@


if( $IsLinux ) {
    $platform = "Linux"
}
elseif( $IsMacOS ) {
    $platform = "MacOS"
}
elseif( $IsWindows ) {
    $platform = "Windows"
} else {
    $platform = "Unknown"
}

$targetRoot = "$root\$target"

Write-Output @"

  platform    = $platform
  targetRoot  = $targetRoot
"@

# Get script count
$buildScripts = @( Get-Item $targetRoot/$platform*.ps1 `
    | Where-Object Name -Match "$scriptFilter" `
    | Where-Object Name -NotMatch 'build' `
    | Where-Object Name -NotMatch 'actions' `
    | ForEach-Object { $_.Name } )

$scriptCount = $buildScripts.count
Write-Output @"

  scriptFilter = $scriptFilter
  Script count: $scriptCount
"@

#Fail if no scripts
if( $scriptCount -eq 0 ) {
    Write-Error "No build scripts found"
    exit 1
}

# Print Scripts
Write-Output "  Scripts:"
$buildScripts | ForEach-Object { Write-Output "    $_" }

if( $list ) {
    exit
}

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

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

[array]$summary = @()

# Process Scripts
foreach( $script in $buildScripts ) {

    H3 "Starting $script"
    $config = Split-Path -Path $script -LeafBase
    $Host.UI.RawUI.WindowTitle = "$target | $config"

    $traceLog = "$targetRoot\logs-raw\$config.txt"
    $cleanLog = "$targetRoot\logs-clean\$config.txt"
    Write-Output "    traceLog   = $traceLog"
    Write-Output "    cleanLog   = $cleanLog"

    # set default environment and commands.
    $envRun = "pwsh"
    $envActions = "$platform-actions.ps1"
    $envClean = "CleanLog"

    # source command overrides
    . "$targetRoot/$script" "get_env"
    
    $statistics = [PSCustomObject]@{
        target      = "$target"
        config      = "$config"
        status      = "dnf"
        duration    = "dnf"
        fetch       = ""
        prepare     = ""
        build       = ""
        test        = ""
    }
    
    $timer = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        &$envRun "-Command" @"
`$root='$root'
`$targetRoot='$targetRoot'
`$platform='$platform'
`$target='$target'
`$gitBranch='$gitBranch'
`$fetch='$fetch'
`$prepare='$prepare'
`$build='$build'
`$jobs='$jobs'
`$test='$test'
`$fresh='$fresh'
`$append='$append'
`$verbose='$verbose'
`$script='$script'
$targetRoot/$envActions
"@ 2>&1 | Tee-Object "$traceLog"
        ($statistics).status = "Completed"
    } catch {
        Write-Output "Error during $config"
    }
    
    $timer.Stop()
    ($statistics).duration = $timer.Elapsed
    
    # Try to fetch any stats from the bottom of the file.
    Get-Content "$traceLog" | Select-Object -Last 20 | ForEach-Object {
        if( $_.StartsWith( '($statistics).' ) ) {
            Invoke-Expression "$_"
        }
    }
    
    $summary += $statistics
    
    H3 Process Logs
    &$envClean "$traceLog" > $cleanLog
}

H3 "Finished"
H4 "Original Command: $($(Get-PSCallStack)[0].InvocationInfo.Line)"
H4 "Summary"
$summary | Format-Table -Property target,config,fetch,prepare,build,test,status,duration