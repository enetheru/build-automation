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

# THis enables unicode characters to show up in the console
$OutputEncoding = New-Object System.Text.UTF8Encoding
[console]::InputEncoding = $OutputEncoding
[console]::OutputEncoding = $OutputEncoding

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap { Start-Sleep -Seconds 1 }

function Syntax {
    Write-Output 'Syntax: ./build.sh -[fpbt] [-scriptFilter <regex>] <target>'
}

# Default and Detected Settings
if(     $IsLinux    ) { $platform = "Linux" }
elseif( $IsMacOS    ) { $platform = "MacOS" }
elseif( $IsWindows  ) { $platform = "Windows" }
else { $platform = "Unknown" }

$root = $PSScriptRoot

# Verbose Preference is a standard option.
$verbose = ($VerbosePreference -eq "Continue") ? $true : $false

if( -Not ($fetch -Or $prepare -Or $build -Or $test) ) {
    $fetch = $true; $prepare = $true; $build = $true; $test = $true
}

$targetRoot = "$root\$target"

. ./share/format.ps1

H1 "AutoBuild"
H2 "Options"

Write-Output @"
  platform    = $platform
  root        = $root
  command     = '$($(Get-PSCallStack)[0].InvocationInfo.Line)'

  fetch       = $fetch
  prepare     = $prepare
  build       = $build
  test        = $test
  
  proc_count  = $jobs

  fresh build = $fresh
  log append  = $append

  target      = $target
  targetRoot  = $targetRoot
  branch      = $gitBranch
"@

if( $target -eq "" ) {
    Syntax
    Write-Error "Missing <target>"
}

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

if( $list ) { exit }

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

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

[array]$savedVars = @(
   "`$verbose   ='$verbose'",
   "`$jobs      ='$jobs'",
   "`$platform  ='$platform'",
   "`$root      ='$root'",
   "`$targetRoot='$targetRoot'",
   "`$target    ='$target'",
   "`$gitBranch ='$gitBranch'",
   "`$fetch     ='$fetch'",
   "`$prepare   ='$prepare'",
   "`$build     ='$build'",
   "`$test      ='$test'",
   "`$fresh     ='$fresh'",
   "`$append    ='$append'"
)

[array]$summary = @()

# Process Scripts
foreach( $script in $buildScripts ) {
    #reset variables
#    foreach( $var in $savedVars){ &"$var" }

    H3 "Using $script"
    $config = Split-Path -Path $script -LeafBase
    $Host.UI.RawUI.WindowTitle = "$config"

    $traceLog = "$targetRoot\logs-raw\$config.txt"
    $cleanLog = "$targetRoot\logs-clean\$config.txt"

    # set default environment and commands.
    $envRun = "pwsh"
    $envActions = "$platform-actions.ps1"
    $envClean = "CleanLog"

    # source command overrides
    H4 "Source variations from: '$targetRoot/$script'"
    . "$targetRoot/$script" "get_env"
    
    $statistics = [PSCustomObject]@{
        target      = "$target"
        config      = "$config"
        fetch       = ""
        prepare     = ""
        build       = ""
        test        = ""
        status      = "dnf"
        duration    = "dnf"
    }
    
    $useVars = @(
        "`$root         = '$root'",
        "`$targetRoot   = '$targetRoot'",
        "`$platform     = '$platform'",
        "`$target       = '$target'",
        "`$gitBranch    = '$gitBranch'",
        "`$fetch        = '$fetch'",
        "`$prepare      = '$prepare'",
        "`$build        = '$build'",
        "`$jobs         = '$jobs'",
        "`$test         = '$test'",
        "`$fresh        = '$fresh'",
        "`$append       = '$append'",
        "`$verbose      = '$verbose'",
        "`$script       = '$script'",
        "`$traceLog     = '$traceLog'",
        "`$cleanLog     = '$cleanLog'"
    )
    
    if( $verbose -eq 1) {
        H5 "Command: $envRun"
        H5 "With:`n`t$($useVars -Join '`n`t')"
        H5 "Action: $targetRoot/$envActions"
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
    
    H3 "$config - Statistics"
    $summary += $statistics
    
    H3 "Process Logs"
    &$envClean "$traceLog" > $cleanLog
}

Figlet -c "Finished"
H4 "Original Command: $($(Get-PSCallStack)[0].InvocationInfo.Line)"

if( $buildScripts.Length -gt 1 ) {
    H4 "Summary"
    $summary | Format-Table -Property target,config,fetch,prepare,build,test,status,duration
}