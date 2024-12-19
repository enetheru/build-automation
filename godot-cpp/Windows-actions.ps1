#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c ) {
    # [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
    [System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"
    if( $gitBranch -eq "" ){ $gitBranch = "name_clash" }
    
    # This function is called when the build is completed to whittle down the
    # build log to something usable. It can be overridden in the build script.
    function CleanLog {
        H3 "This is a generic CleanLog function."
#        https://learn.microsoft.com/en-us/dotnet/standard/base-types/regular-expression-language-quick-reference
        
        $msvcPath   = 'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.42.34433\bin\HostX64\x64\'
        $mingwPath  = 'C:\mingw64\bin\'
        $llvmPath   = 'C:\PROGRA~1\LLVM\bin\'
        $ndkPath    = 'C:\androidsdk\ndk\23.2.8568313\toolchains\llvm\prebuilt\windows-x86_64\bin\'
        $ndkPath2   = 'C:\androidsdk/ndk/23.2.8568313/toolchains/llvm/prebuilt/windows-x86_64/bin/'
        $emsdkPath  = 'C:\emsdk\upstream\emscripten\'
        $cmakePath  = 'C:\Program Files\CMake\bin\'
        
        $lineMatch = '^  󰞷 (cmake|scons)' # Commands to keep
        $lineMatch += '|== (Config|Target)' # Info to keep
        $lineMatch += '|editor_plugin_registration.cpp'
        $lineMatch += '|libgdexample.*\.dll'
        $lineMatch += '|libgodot-cpp.*\.(a|lib)'
        
        $notMatch = 'nomatch' #'rm -f|vcxproj'
        $notMatch += '|^\[....\].*'
        $notMatch += '|^  Removing.*'
        
        $erase = "==+-?|󰞷 "
        $erase += "|$([Regex]::Escape("$buildRoot\"))"
        $erase += "|$([Regex]::Escape($msvcPath))"
        $erase += "|$([Regex]::Escape($mingwPath))"
        $erase += "|$([Regex]::Escape($llvmPath))"
        $erase += "|$([Regex]::Escape($ndkPath))"
        $erase += "|$([Regex]::Escape($ndkPath2))"
        $erase += "|$([Regex]::Escape($emsdkPath))"
        $erase += "|$([Regex]::Escape($cmakePath))"
        
        $joins = '(Target|Config):|Removing'
        $joins += '-E|-j|--build|-t|--target|--config'   # CMake/SCons
        $joins += '|-o|-MT|-MF'         # gcc Options
        $joins += '|/D'                 # MSVC Options
        
        $spaceBefore  = ".*exe`$"
        $spaceBefore += "|ar`$|g\+\+`$"              # gcc
        $spaceBefore += "|^em[+]+|^emar|^emranlib"  # Emscripten
        $spaceBefore += "|^cl|^lib|^link"           # MSVC
        $spaceBefore += "|^clang[+]+|^llvm-ar"      # clang
        
        $prevLine = "NotMatch"
        $prevOpt = $null
        Get-Content "$args" | ForEach-Object { # Split commands that are joined
            $_ -csplit ' && | -- '
        } `
        | Where-Object {    # match and not match.
             $true -and ($_ -Match "$lineMatch") -and ($_ -notmatch "$notMatch")
            
        } `
        | Where-Object { # Skip lines that start with the same 80 chars
            -Not ($_ -cmatch "${prevLine}.*")
            $prevLine = [Regex]::Escape($_.Substring( 0,[int]::min( $_.Length, 80 ) ) );
        } `
        | ForEach-Object {  # erase, trim, split, then remove lines that start the same
            $prev = "NotMatch"
            ($_ -creplace "$erase", "").Trim() -cSplit '\s+' | ForEach-Object {
                if( -Not ($_ -cmatch "${prev}.*") ){
                    $prev = [Regex]::Escape($_.Substring(0,[int]::min( $_.Length, 10 ))); $_
                }
            }
        } `
        | ForEach-Object {  # Re-Join Lines
            if( $prevOpt ) { "$prevOpt $_"; $prevOpt = $null }
            elseif( $_ -cmatch "^$joins" ) { $prevOpt = "$_" }
            else { $_ }
        } `
        | ForEach-Object {  # Embellish to make easier to read
            $_  -creplace '"cmake.exe"','cmake.exe'`
                -creplace '^(Config)',"`n## `$1" `
                -creplace '^(Target)','## $1' `
                -creplace "^([^-/]$spaceBefore)","`n`$1"
        }
        
        return
        # TODO Clear default flags, and irrelevant flags
        # GNU
        # LLVM
        # MSVC
        # MinGW
        # Emscripten
        # Android
        "fp:precise",
        "Gd", "GR", "GS",
        "Zc:forScope", "Zc:wchar_t",
        "DYNAMICBASE", "NXCOMPAT", "SUBSYSTEM:CONSOLE", "TLBID:1",
        "errorReport:queue", "ERRORREPORT:QUEUE", "EHsc",
        "diagnostics:column", "INCREMENTAL", "NOLOGO", "nologo"
    }
    return
}

# Setup Powershell Preferences
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4#verbosepreference
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

. "$root\share\format.ps1"
. "$root\share\build-actions.ps1"

$stats = [PSCustomObject]@{}

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Host $_
    Finalise $stats
    Start-Sleep -Seconds 1
}

#### Setup our variables

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

$targetRoot = $thisScript  | split-path -parent

$config = Split-Path -Path $script -LeafBase

$buildRoot = "$targetRoot\$config"

# Custom Variables
[string]$godot = 'C:\build\godot\Windows-windows-msvc\bin\godot.windows.editor.x86_64.exe'
[string]$godot_tr = 'C:\build\godot\Windows-windows-msvc\bin\godot.windows.template_release.x86_64.exe'
[string]$godot_td = 'C:\build\godot\Windows-windows-msvc\bin\godot.windows.template_debug.x86_64.exe'

#### Write Summary ####
SummariseConfig

# Add custom things to Summary
Write-Output @"
  godot.editor           = $godot
  godot.template_release = $godot_tr
"@

# Prepare with SCons
# In the case of godot-cpp we can generate the bindings without building the library
# It will auto generate the bindings, or we can force it if fresh is enabled.
function PrepareScons {
    param(
        [Alias( "v" )] [array] $vars = @()
    )
    # requires SConstruct file existing in the current directory.
    if( -Not (Test-Path "SConstruct" -PathType Leaf) ) {
        Write-Error "PrepareScons: Missing '$(Get-Location)\SConstruct'"
        Return 1
    }
    
    Figlet -f "small" "SCons Prepare"
    
    # SCons - Remove generated source files if exists.
    $doFresh = ($fresh -eq $true) ? "generate_bindings=yes" : $null
    $doVerbose  = ($verbose -eq $true) ? "verbose=yes" : $null
    $buildVars = @(
        "$doVerbose",
        "$doFresh",
        'build_library=no',
        'compiledb=yes',
        "compiledb_file='$config.json'"
    ) + $vars
    
    # Binding Generation is effected by three variables
    # arch -  Target Architecture, either 32 or 64, FIXME default unknown, I guess host architecture?
    # generate_template_get_node -  default is 'yes'.
    # precision -  single/double, default is 'single'.
    Format-Eval "scons $($buildVars -Join ' ')"
}

# SCons - Remove generated source files if exists.
function EraseGen {
    
    if( Test-Path "$buildRoot\gen" -PathType Container ) {
        H4 "Removing Generated Files"
        Remove-Item -LiteralPath "$buildRoot\gen" -Force -Recurse
    }
}

function WaitingForGodot {
    # Godot spawns and detaches another process, making this harder than it needs to be.
    # FIXME find a way to get the actual process ID that I want to wait on.
    while( Get-Process | Where-Object -Property "ProcessName" -Match "godot" ) {
        #This is a slightly better fix than before, but I still want to get the specific process.
        Start-Sleep -Milliseconds 15
    }
}

function TestCommon {
    Figlet "Test"
    $projectDir="$buildRoot\test\project"
    
    if( -Not (Test-Path "$projectDir\bin\libgdexample.windows.template_release.x86_64.dll" -PathType Leaf) ) {
        Write-Error "Missing libgdexample.windows.template_release.x86_64.dll"
        return 1
    }
    
    if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        & {
            $PSNativeCommandUseErrorActionPreference = $false
            &$godot -e --path "$projectDir" --quit --headless *> $null
            WaitingForGodot
        }
        if( -Not (Test-Path "$projectDir\.godot" -PathType Container) ) {
            Write-Error "Failed to create .godot folder" >> "$targetRoot\summary.log"
        }
    }

    H4 "Run the test project"
    Format-Command "$godot_tr --path `"$buildRoot\test\project\`" --quit --headless`n"
    
    H4 "Run the test project"
    $script:result = ("unknown")
    & {
        $PSNativeCommandUseErrorActionPreference = $false
        Format-Command "$godot_tr --path `"$projectDir`" --quit --headless"
        &$godot_tr --path "$projectDir" --quit --headless | Out-String
        WaitingForGodot
    } | Tee-Object -Variable result
    
    if( @($result | Where-Object { $_ })[-1] -Match "PASSED" ) {
        Write-Output "Test Succeded"
    } else {
        Write-Error "Test-Failure"
    }
}

Set-Location "$targetRoot"

# Per config Overrides and functions
. "$targetRoot\$script"

H3 "$config - Processing"

DefaultProcess

H2 "$config - Completed"

Finalise $stats
Start-Sleep 1
