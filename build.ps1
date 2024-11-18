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


[CmdletBinding(PositionalBinding=$false)]
param(
    [Alias("f")] [switch] $fresh,
    [Alias("a")] [switch] $append,
    [Alias("n")] [switch] $noTest,
    [Parameter(Position = 0)] [string] $target,
    [Parameter(Position = 1)] [string] $regexFilter,
    [Parameter(ValueFromRemainingArguments=$true)]$passThrough
# Remaining arguments are treated as targets
)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if( $regexFilter -eq "--" ){
    Clear-Variable -name regexFilter
}

# shellcheck disable=SC2034
$columns=120

. ./share/format.ps1

H1 "AutoBuild"

function Syntax {
   Write-Output 'Syntax: ./build.sh [-hfa] [--longopts] <target> ["regexFilter"]'
}

H2 " Options "

Write-Output @"
  command     = '$($(Get-PSCallStack)[0].InvocationInfo.Line)'
  fresh       = $fresh
  append      = $append
  test        = $noTest
  target      = $target
  regexFilter = $regexFilter
  passThrough = $passThrough
"@

if( $target -eq "" ){
    Syntax
    Write-Error "Missing <target>"
}

#Center " Automatic " "$(Fill "- " )"
Fill "- " | Center " Automatic "

if( $IsLinux ){
    $platform="Linux"
} elseif( $IsMacOS ){
    $platform="MacOS"
} elseif( $IsWindows ){
    $platform="Windows"
} else{
    $platform="Unknown"
}
Write-Output "  platform    = $platform"

$root=$PSScriptRoot
Write-Output "  root        = $root"

$targetRoot="$root\$target"
Write-Output "  targetRoot  = $targetRoot"

$mainScript="$root\$target\$platform-build.ps1"
Write-Output "  script      = $mainScript"

# shellcheck disable=SC1090
## Run target build script ##
. $mainScript
