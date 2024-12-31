#!/usr/bin/env pwsh
#Requires -Version 7.4

## Check whether this file is sourced or not.
#if( -Not ($MyInvocation.InvocationName -eq '.') ) {
#    Write-Output "Do not run this script directly, it simply holds helper functions"
#    exit 1
#}

# Dot Source Guard
if( $SOURCE_WINDOWS_CONFIG_SH ){ "Do not source multiple times"; exit }
$SOURCE_WINDOWS_CONFIG_SH=$true

#TEMPORARY FIX
. ../share/format.ps1
$jobs = 1
$verbose = 1

function BuildScons {
    param(
        [PSCustomObject]$buildConfig,
        [array] $vars   = @(),
        [string]$target
    )
    
    # requires SConstruct file existing in the current directory.
    # SCons - Remove generated source files if exists.
    if( -Not (Test-Path "SConstruct" -PathType Leaf) ) {
        Write-Error "BuildSCons: Missing '$(Get-Location)\SConstruct'"
#        Return 1
    }
    
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    
    $buildVars = @( "$doJobs", "$doVerbose") + $vars
    
    Figlet -f "small" $this.Name
    H3 "Config: ${buildConfig}"
    H3 "Target: $target"
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
#        Format-Eval "scons $($buildVars -Join ' ') target=$target"
    Write-Output "scons $($buildVars -Join ' ') target=$target"
    Start-Sleep -Seconds 1
        
    $timer.Stop()
    $ts = $timer.Elapsed
    $this.duration = "{0:00}:{1:00}:{2:00}" -f $ts.Hours, $ts.Minutes, $ts.Seconds
    $this.status = 'completed'
        
    H3 "BuildScons Completed"
        
    Fill "-"
}

# Construct scons builder object
$sconsBuild = [PSCustomObject]@{
    Name        = "SCons Build"
    status      = "dnf"
    duration    = [System.Timespan]0
}
$sconsBuild | Add-Member -MemberType 'ScriptMethod' -Name "Command" -Value ${Function:BuildScons}

# Construct build configurations
[array]$buildConfigs  = @()

# First Build Config
$buildConfig = [PSCustomObject]@{
    Name    = "Windows.scons.template_debug"
    gitUrl  = [System.Uri] "http://github.com/enetheru/godot-cpp.git"
    gitHash = ""
    buildCommand = [PSCustomObject]$sconsBuild
}
$buildConfig | Add-Member -MemberType 'ScriptMethod' -Name "Build" -Value {
    $this.buildCommand.Command( $this.Name, @("var1","var2"), "template_debug" )
}
$buildConfigs += $buildConfig

# Second Build Config.
$buildConfig = [PSCustomObject]@{
    Name    = "Windows.scons.template_release"
    gitUrl  = [System.Uri] "http://github.com/enetheru/godot-cpp.git"
    gitHash = ""
    buildCommand = [PSCustomObject]$sconsBuild
}
$buildConfig | Add-Member -MemberType 'ScriptMethod' -Name "Build" -Value {
    $this.buildCommand.Command( $this.Name, @("var1","var2"), "template_release" )
}
$buildConfigs += $buildConfig

# Run Build Configurations
$buildConfigs | ForEach-Object {
    $_ | Get-Member | Format-Table
    $_.Build()
    $_.buildCommand
}

# Report Statistics
$buildConfigs | ForEach-Object {
    H3 $_.Name
    $_.buildCommand | Format-Table
    
}



#{cmake,meson}
#{make,ninja,scons,msvc,autotools,gradle,etc}
#{gcc,clang,msvc,appleclang,ibm,etc}
#{ld,lld,gold,mold,appleld,msvc}
