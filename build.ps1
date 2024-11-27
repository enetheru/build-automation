#!/usr/bin/env pwsh
#Requires -Version 7.4

<#
.SYNOPSIS
    Build all the things
.DESCRIPTION
    I kept repeating myself, changing directories, forgetting commands,
    so I thought I would automate it all away, this my attempt at doing so.
    My ADHD and completionist mind makes me write these help things.
.PARAMETER Fresh
    Perform a cleanup prior to building
.PARAMETER Append
    Add to the build logs, rather than clobber them on each build
.PARAMETER NoTest
    Dont perform testing
.PARAMETER Target
    The target project to build
.PARAMETER regexFilter
    An extended regex filter to use when looking for build scripts
.EXAMPLE
    ./build godot-cpp
    Will build all available configuration from the host system.
.NOTES
    Author: Samuel Nicholas
    Date:   2024-11-15
#.LINK
#    http://whatver.com
.
#>


[CmdletBinding( PositionalBinding = $false )]
param(
    [Alias( "f" )] [switch] $fetch,
    [Alias( "c" )] [switch] $configure,
    [Alias( "b" )] [switch] $build,
    [Alias( "t" )] [switch] $test,

    [switch] $fresh,        # re-fresh the configuration
    [switch] $clean,        # clean the build directory
    [switch] $append,       # Append to the logs rather than clobber
    [string] $regexFilter = ".*",    #Filter which scripts are used.

    [Parameter( Position = 0 )] [string] $target,       # Which target to use
    [Parameter( Position = 1 )] [string] $gitBranch,    # Which git branch to use

    [Parameter( ValueFromRemainingArguments = $true )]$passThrough #All remaining arguments
)
# Remaining arguments are treated as targets

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Start-Sleep -Seconds 1
}

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if( -Not( $fetch -Or $configure -Or $build -Or $test)){
    $fetch=$true; $configure=$true; $build=$true; $test=$true
}

if( $regexFilter -eq "--" ) {
    Clear-Variable -name regexFilter
}

# shellcheck disable=SC2034
$columns = 120

. ./share/format.ps1

H1 "AutoBuild"

function Syntax {
    Write-Output 'Syntax: ./build.sh [-hfa] [--longopts] <target> ["regexFilter"]'
}

H2 "Options"

Write-Output @"
  command     = '$($(Get-PSCallStack)[0].InvocationInfo.Line)'
  fetch       = $fetch
  configure   = $configure
  build       = $build
  test        = $test

  fresh build = $fresh
  log append  = $append

  target      = $target
  branch      = $gitBranch
  
  regexFilter = $regexFilter
  passThrough = $passThrough
"@

if( $target -eq "" ) {
    Syntax
    Write-Error "Missing <target>"
}

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

$root = $PSScriptRoot
$targetRoot = "$root\$target"
$mainScript = "$root\$target\$platform-build.ps1"

Fill "- " | Center " Automatic "
Write-Output @"
  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
  script      = $mainScript
"@

# shellcheck disable=SC1090
## Run target build script ##

&$mainScript -f:$fetch -c:$configure -b:$build -t:$test -regexFilter $regexFilter $gitBranch $passThrough
# -VHDL2008:$VHDL2008.IsPresent
