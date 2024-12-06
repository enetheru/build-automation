#!/usr/bin/env pwsh
#Requires -Version 7.4

[CmdletBinding( PositionalBinding = $false )]
param(
    [Alias( "f" )] [switch] $fetch,
    [Alias( "c" )] [switch] $configure,
    [Alias( "b" )] [switch] $build,
    [Alias( "t" )] [switch] $test,

    [switch] $list,                 # show the list of scripts and exit
    [switch] $fresh,                # re-fresh the configuration
    [switch] $clean,                # clean the build directory
    [switch] $append,               # Append to the logs rather than clobber
    [string] $scriptFilter = ".*",  # Filter which scripts are used.

    [Parameter( Position = 0 )] [string] $target,       # Which target to use
    [Parameter( Position = 1 )] [string] $gitBranch,    # Which git branch to use

    [Parameter( ValueFromRemainingArguments = $true )]$passThrough #All remaining arguments
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$OutputEncoding = New-Object System.Text.UTF8Encoding
[console]::InputEncoding = $OutputEncoding
[console]::OutputEncoding = $OutputEncoding

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Start-Sleep -Seconds 1
}

$root = $PSScriptRoot

. ./share/format.ps1

function Syntax {
    Write-Output 'Syntax: ./build.sh -[fcbt] [-scriptFilter <regex>] <target>'
}

H1 "AutoBuild"
H2 "Options"

if( -Not ($fetch -Or $configure -Or $build -Or $test) ) {
    $fetch = $true; $configure = $true; $build = $true; $test = $true
}

Write-Output @"
  command     = '$($(Get-PSCallStack)[0].InvocationInfo.Line)'
  root        = $root

  fetch       = $fetch
  configure   = $configure
  build       = $build
  test        = $test

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

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

# Process Scripts
foreach( $script in $buildScripts ) {

    H3 "Starting $script"
    $config = Split-Path -Path $script -LeafBase

    $traceLog = "$targetRoot\logs-raw\$config.txt"
    $cleanLog = "$targetRoot\logs-clean\$config.txt"
    Write-Output "    traceLog   = $traceLog"
    Write-Output "    cleanLog   = $cleanLog"

    # set default environment and commands.
    $envRun = "pwsh"
    $envActions = "$platform-actions.ps1"
    $envClean = "CleanLog-Default"

    # source command overrides
    . "$targetRoot/$script" "get_env"

    &$envRun "-Command" @"
`$root='$root'
`$targetRoot='$targetRoot'
`$platform='$platform'
`$target='$target'
`$gitBranch='$gitBranch'
`$fetch='$fetch'
`$configure='$configure'
`$build='$build'
`$test='$test'
`$fresh='$fresh'
`$append='$append'
`$verbose='$VerbosePreference'
`$script='$script'
$targetRoot/$envActions
"@ 2>&1 | Tee-Object "$traceLog"

    # Cleanup Logs
    &$envClean "$traceLog" > $cleanLog
}