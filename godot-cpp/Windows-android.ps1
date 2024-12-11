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

function Prepare {
    H1 "Prepare"
    $doFresh = ($fresh -eq $true) ? "--fresh" : $null
    
    Set-Location "$buildRoot"
    EraseKeyObjects

    # Create Build Directory if it doesn't already exist.
    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
        H4 "Creating $buildDir"
        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
    }
    Set-Location $buildDir
    
    H1 "CMake Configure"
    [array]$cmakeVars = @()
    $cmakeVars += "-GNinja"
    $cmakeVars += "--toolchain `"C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake`""
    $cmakeVars += "-DCMAKE_BUILD_TYPE=Release"
    $cmakeVars += "-DGODOT_ENABLE_TESTING=YES"
    $cmakeVars += "-DANDROID_PLATFORM=android-29"
    $cmakeVars += "-DANDROID_ABI=x86_64"
    
    Format-Eval "cmake $doFresh .. $($cmakeVars -Join ' ')"
}

function Build {
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    #CMake verbose
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    
    # FIXME get arch somehow.
    $arch = "x86_64"
    
    
    [array]$statArray = @()
    
    $targets = @(
        "template_debug",
        "template_release",
        "editor"
    )

    # Build Targets using CMake
    Set-Location $buildDir
    foreach( $target in $targets ){
        H2 "$target"; H1 "CMake Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "cmake --build . $doJobs $doVerbose -t godot-cpp.test.$target"
        
        $timer.Stop()
        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$arch.$target.$arch.so"
        
        $statArray += [PSCustomObject] @{
            target      = "cmake.$target"
            duration    = $timer.Elapsed
            size        = DisplayInBytes $artifact.Length
        }
        EraseBinaries
    }
    
    #SCons verbose
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    
    [array]$sconsVars = @()
    $sconsVars += "platform=android"
    $sconsVars += "arch=x86_64"

    # Build Targets using SCons
    Set-Location "$buildRoot/test"
    
    foreach( $target in $targets ){
        H2 "$target"; H1 "Scons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()

        Format-Eval "scons $doJobs $doVerbose target=$target $($sconsVars -Join ' ')"
        
        $timer.Stop()
        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$target.$arch.so"
        
        $statArray += [PSCustomObject] @{
            target      = "scons.$target"
            duration    = $timer.Elapsed
            size        = DisplayInBytes $artifact.Length
        }
        EraseBinaries
    }

    # Report Results
    $statArray | Format-Table
}