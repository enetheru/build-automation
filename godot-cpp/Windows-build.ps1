#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    [Alias( "f" )] [switch] $fetch,
    [Alias( "c" )] [switch] $configure,
    [Alias( "b" )] [switch] $build,
    [Alias( "t" )] [switch] $test,

    [switch] $fresh = $fresh,
    [switch] $append = $append,
    [string] $regexFilter = ".*",

    [Parameter( Position = 1 )] [string] $gitBranch = "master",

    [Parameter( ValueFromRemainingArguments = $true )]$passThrough = $passThrough
)
# Remaining arguments are treated as targets

# Because CLion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.

trap {
    Write-Output "trap triggered on exception. Sleeping 1"
    Set-Location $root
    Start-Sleep -Seconds 1
}

# PowerShell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if( -Not( $fetch -Or $configure -Or $build -Or $test)){
    $fetch=$true; $configure=$true; $build=$true; $test=$true
}

$verbose=$verbosePreference

$prev_dir = $(Get-Location)

$platform = "Windows"
$target = "godot-cpp"

# $root = $(Get-PSCallStack)[0].InvocationInfo.ScriptName | Split-Path
# . $root/share/format.ps1

[string]$thisScript = $(Get-PSCallStack)[0].scriptName

H2 "Build $target using $platform"

Write-Output @"
  thisScript  = $thisScript
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

# Main Variables
[string]$godot = "C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr = "C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

Write-Output @"

  godot.editor           = $godot
  godot.template_release = $godot_tr
"@

# [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
[System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"
# [string]$gitBranch = "ipo-lto"

Write-Output @"

  gitUrl      = $gitUrl
  gitBranch   = $gitBranch
"@

# Get the target root from this script location
$targetRoot = $thisScript  | split-path -parent
Write-Output @"

  platform    = $platform
  root        = $root
  targetRoot  = $targetRoot
"@

cd "$targetRoot"

# Get script count
$buildScripts = @( Get-Item ./$platform*.ps1 `
    | Where-Object Name -Match "$regexFilter" `
    | Where-Object Name -NotMatch 'build' `
    | %{ $_.Name } )

$scriptCount = $buildScripts.count
Write-Output "`n  Script count: $scriptCount"

#Fail if no scripts
if( $scriptCount -eq 0 ) {
    cd "$prev_dir"
    Write-Error "No build scripts found"
    exit 1
}

# Print Scripts
Write-Output "  Scripts:"
foreach( $script in $buildScripts ) {
    Write-Output "    $script"
}

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

# Some steps are identical.
function PrepareCommon {

    # Clean up key artifacts to trigger rebuild
    [array]$artifacts = @($(rg -u --files "$buildRoot" `
        | rg "(memory|example).*?o(bj)?$"))

    $artifacts += @($(rg -u --files "$buildRoot" `
        | rg "\.(a|lib|so|dll|dylib|wasm32|wasm)$"))
    #    ($array1 + $array2) | Select-Object -Unique -Property Name

    #Ignore exit code from ripgrep failure to match files.
    $global:LASTEXITCODE = 0

    if( $artifacts.Length -gt 0 ) {
        H3 "Removing key Artifacts"
        $artifacts | Sort-Object | Get-Unique | %{
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
}

function TestCommon {
    H1 "Test"

    Write-Output "" >> "$targetRoot\summary.log"
    H4 "$config" >> "$targetRoot\summary.log"

    if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
        H4 "Generate the .godot folder"
        Format-Command "$godot -e --path `"$buildRoot\test\project`" --quit --headless"
        & $godot -e --path "$buildRoot\test\project" --quit --headless 2>&1 | Tee-Object -Variable result
        Start-Sleep -Seconds 1

        if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) ) {
            Write-Output "Failed to create .godot folder" >> "$targetRoot\summary.log"
            return 1
        }
    } else {
        H4 "The .godot folder has already been generated."
    }

    H4 "Run the test project"
    Format-Command "$godot_tr --path `"$buildRoot\test\project\`" --quit --headless`n"
    & $godot_tr --path "$buildRoot\test\project\" --quit --headless | Tee-Object -Variable result
    @($result.split( "`r`n" ) | ? { $_ -Match "FINI|PASS|FAIL|Godot" }) >> "$targetRoot\summary.log"
}


function RunActions {
    H2 "Processing - $config"

    $buildRoot = "$targetRoot\$config"
    Write-Output "  buildRoot  = $buildRoot"

    . "$root\share\build-actions.ps1"
    . "$targetRoot\$script"

    if( $fetch ) {
        Fetch 2>&1
        if( $LASTEXITCODE ) {
            Write-Error "Fetch-Failure"
        }
    }

    if( $configure ) {
        Prepare 2>&1
        if( $LASTEXITCODE ) {
            Write-Error "Prep-Failure"
        }
    }

    if( $build ){
        Build 2>&1
        if( $LASTEXITCODE ) {
            Write-Error "build-Failure"
        }
    }

    if( $test ){
        $result=("unknown")
        Test 2>&1 | Tee-Object -Variable result
        if( @($result | ? { $_ })[-1] -Match "PASSED" ) {
            Write-Output "Test Succeded"
        } else {
            Write-Output "Test-Failure"
        }
    }

    Clean 2>&1
    if( $LASTEXITCODE ) {
        Write-Output "Clean-Failure"
    }

    H3 "Completed - $config"
}

# Process Scripts
foreach( $script in $buildScripts ) {
    H2 "using $script ..."

    $config = Split-Path -Path $script -LeafBase

    $traceLog = "$targetRoot\logs-raw\$config.txt"
    $cleanLog = "$targetRoot\logs-clean\$config.txt"
    Write-Output "  traceLog   = $traceLog"
    Write-Output "  cleanLog   = $cleanLog"

    try {
        RunActions 2>&1 | Tee-Object -FilePath "$traceLog"
    } catch {
        Get-Error
        exit
    }

    $matchPattern = 'register_types|memory|libgdexample|libgodot-cpp|  =>| ==|  󰞷'
    rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"
}

cd $prev_dir


Start-Sleep -Seconds 1
