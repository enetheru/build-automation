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

$gitBranch = "lto"

function Prepare {
    PrepareCommon
#    $doFresh = ($fresh) ? "--fresh" : $null
#
#    if( -Not (Test-Path -Path "$buildDir" -PathType Container) ) {
#        H4 "Creating $buildDir"
#        New-Item -Path $buildDir -ItemType Directory -Force | Out-Null
#    }
#
#    Set-Location $buildDir
#    H1 "CMake Configure"
#    Format-Eval "cmake $doFresh .. -DGODOT_ENABLE_TESTING=YES -DGODOT_LTO=ON"
}

function Build {
#    $doVerbose = ($verbose) ? "--verbose" : $null
#    $MSBuildOptions = "/nologo /v:m /clp:ShowCommandLine;ForceNoAlign"
#
#    Set-Location $buildDir
#    foreach( $target in @("template_debug", "template_release", "editor") ){
#        H2 "$target"
#        H1 "CMake Build"
#        Format-Eval "cmake --build . $doVerbose -t godot-cpp.test.$target --config Release -- $MSBuildOptions"
#    }

    Set-Location "$buildRoot/test"
    foreach( $target in @("template_debug", "template_release", "editor") ){
        H2 "$target"
        H1 "Scons Build"
        Format-Eval "scons -j $jobs target=$target lto=full"
    }

    Get-ChildItem .\project\bin\*.dll | ForEach-Object { @{$_.Name=$(DisplayInBytes $_.Length)} }
}
