#!/usr/bin/env pwsh
#Requires -Version 7.4

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}

# tell the build command how to run ourselves.
if( $args -eq "get_env" ) {
    H4 "Using Default env Settings"
    return
}

$script:buildDir = "$buildRoot/cmake-build"

$gitBranch = "build_profile"

function Prepare {
    PrepareCommon
    $doFresh = ($fresh) ? "--fresh" : $null

    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }

    Set-Location $buildDir
    H1 "CMake Configure"

    [array]$cmakeVars = $null
    $cmakeVars += "-DGODOT_ENABLE_TESTING=YES"
    $cmakeVars += "-DGODOT_BUILD_PROFILE=test/build_profile.json"
    
    Format-Eval "cmake $doFresh .. $($cmakeVars -Join ' ')"
}

function Build {
    $doVerbose = ($verbose) ? "--verbose" : $null
    $MSBuildOptions = "/nologo /v:m /clp:`"ShowCommandLine;ForceNoAlign`""


    Set-Location $buildDir
    foreach( $target in @("template_debug", "template_release", "editor") ){
        H2 "$target"; H1 "CMake Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "cmake --build . $doVerbose -t godot-cpp.test.$target --config Release -- $MSBuildOptions"
        
        H4 "$target duration: $($timer.Stop();$timer.Elapsed)"
    }

    # Report file sizes
    [array]$files = @()
    Get-ChildItem "$buildRoot\test\project\bin\*.dll" | ForEach-Object {
        $files += @{ name=$_.Name; size=(DisplayInBytes $_.Length) } 
    }
    $files | Select-Object name,size

    Set-Location "$buildRoot/test"
    foreach( $target in @("template_debug", "template_release", "editor") ){
        H2 "$target"; H1 "Scons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()

        Format-Eval "scons -j $jobs target=$target build_profile=build_profile.json"
        
        H4 "$target duration: $($timer.Stop();$timer.Elapsed)"
    }

    # Report file sizes
    [array]$files = @()
    Get-ChildItem "$buildRoot\test\project\bin\*.dll" | ForEach-Object {
        $files += @{ name=$_.Name; size=(DisplayInBytes $_.Length) } 
    }
    $files | Select-Object name,size
}
