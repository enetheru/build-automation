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
  
  scriptFilter = $scriptFilter
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

Fill "- " | Center " Automatic "
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
Write-Output "`n  Script count: $scriptCount"

#Fail if no scripts
if( $scriptCount -eq 0 ) {
    Write-Error "No build scripts found"
    exit 1
}

# Print Scripts
Write-Output "  Scripts:"
$buildScripts | ForEach-Object { Write-Output "    $_" }

if( $list ){
    exit
}

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

# Process Scripts
foreach( $script in $buildScripts ) {

    H4 "Starting $script"
    $config = Split-Path -Path $script -LeafBase

    $traceLog = "$targetRoot\logs-raw\$config.txt"
    $cleanLog = "$targetRoot\logs-clean\$config.txt"
    Write-Output "  traceLog   = $traceLog"
    Write-Output "  cleanLog   = $cleanLog"

    # set default environment and commands.
    $envRun = "pwsh -c"
    $envClean = "CleanLog-Default"
    # source $envRun and $envActions from script.
    . "$targetRoot/$script" "get_env"

    # Run the action script
    H3 "Start Action"
    &$envRun "-c '. $targetRoot/$envActions'" 2>&1 | Tee-Object "$traceLog"

    # Cleanup Logs
    &$envClean "$traceLog" > $cleanLog


#    try {
#        RunActions 2>&1 | Tee-Object -FilePath "$traceLog"
#    } catch {
#        Get-Error
#        exit
#    }

    # Clean the logs
    # it goes like this, for each line that matches the pattern.
    # split each line along spaces.
    # [repeated per type of construct] re-join lines that match a set of tags
    # the remove the compiler defaults, since CMake adds so many.

    $matchPattern = '^lib|^link|memory|Lib\.exe|link\.exe|  󰞷'
    [array]$compilerDefaults = ("fp:precise", "Gd", "GR", "GS", "Zc:forScope", "Zc:wchar_t",
        "DYNAMICBASE", "NXCOMPAT", "SUBSYSTEM:CONSOLE", "TLBID:1",
        "errorReport:queue", "ERRORREPORT:QUEUE", "EHsc",
        "diagnostics:column", "INCREMENTAL", "NOLOGO", "nologo")
    rg -M2048 $matchPattern "$traceLog" `
        | sed -E 's/ +/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' `
        | sed -E ':a;$!N;s/(Program|Microsoft|Visual|vcxproj|->)\n/\1 /;ta;P;D' `
        | sed -E ':a;$!N;s/(\.\.\.|omitted|end|of|long)\n/\1 /;ta;P;D' `
        | sed -E "/^\/($($compilerDefaults -Join '|'))$/d" > "$cleanLog"
}