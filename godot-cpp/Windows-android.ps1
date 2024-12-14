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

function Prepare {
    Figlet "Prepare"
    
    UpdateAndroid
    
    Set-Location "$buildRoot"
    
    # Erase key files to trigger a re-build so we can capture the build commands.
    # FIXME investigate compile_commands.json for the above purpose
    EraseFiles "editor_plugin_registration" "o|obj"
    
    PrepareScons -v @("platform=android")
    
    [array]$cmakeVars = @(
        "-GNinja",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DGODOT_ENABLE_TESTING=YES",
        "-DANDROID_PLATFORM=android-34",
        "-DANDROID_ABI=x86_64",
        "--toolchain `"C:\androidsdk\ndk\23.2.8568313\build\cmake\android.toolchain.cmake`""
    )
    
    PrepareCMake -v $cmakeVars
}

function Build {
    [array]$statArray = @()
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
#    EraseFiles -f "libgdexample" -e "dll" # FIXME update for android
    
    $llvmPath = 'C:\Program Files\LLVM\bin\'
    H3 "Prepend `$env:path with $llvmPath"
    $savePath = $env:Path
    $env:Path = "$llvmPath;" + $env:Path
    
    Set-Location "$buildRoot\test"
    BuildSCons -v @("use_llvm=yes")
    
    #Restore Path
    $env:Path = $savePath
    
    # Erase previous artifacts
    Set-Location "$buildRoot"
    #    EraseFiles -f "libgdexample" -e "dll" # FIXME update for android
    
    ## CMake Build
    Set-Location "$buildDir\cmake-build"
    BuildCMake
    
    # Report Results
    $statArray | Format-Table
    
    
    
    
    $doJobs     = ($jobs -gt 0) ? "-j $jobs" : $null
    
    # FIXME get arch somehow.
    $arch = "x86" + ([Environment]::Is64BitOperatingSystem) ? "_64" : ""
    
    $targets = @(
        "template_debug",
        "template_release",
        "editor"
    )
    
    # Build Targets using SCons
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    
    [array]$sconsVars = @(
        "platform=android"
        "arch=x86_64"
    )
    
    Set-Location "$buildRoot/test"
    foreach( $target in $targets ){
        H2 "$target"; H1 "Scons Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()

        Format-Eval "scons $doJobs $doVerbose target=$target $($sconsVars -Join ' ')"
        
        $timer.Stop()
        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$target.$arch.so"
        
        $newStat += [PSCustomObject] @{
            target      = "scons.$target"
            duration    = $timer.Elapsed
            size        = DisplayInBytes $artifact.Length
        }
        $newStat | Format-Table
        $statArray += $newStat
    }
    
    # Build Targets using CMake
    $doVerbose  = ($verbose -eq $true) ? "--verbose" : $null
    
    Set-Location "$buildDir"
    foreach( $target in $targets ){
        H2 "$target"; H1 "CMake Build"
        $timer = [System.Diagnostics.Stopwatch]::StartNew()
        
        Format-Eval "cmake --build . $doJobs $doVerbose -t godot-cpp.test.$target"
        
        $timer.Stop()
        $artifact = Get-ChildItem "$buildRoot\test\project\bin\libgdexample.android.$arch.$target.$arch.so"
        
        $newStat += [PSCustomObject] @{
            target      = "cmake.$target"
            duration    = $timer.Elapsed
            size        = DisplayInBytes $artifact.Length
        }
        $newStat | Format-Table
        $statArray += $newStat
    }

    # Report Results
    $statArray | Format-Table
}