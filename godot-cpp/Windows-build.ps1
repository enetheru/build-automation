#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    [Alias("f")] [switch] $fresh,
    [Alias("a")] [switch] $append,
    [Alias("n")] [switch] $noTest,
    [string] $regexFilter
)

# Because Clion starts this script in a pipeline, it errors if the script exits too fast.
# Trapping the exit condition and sleeping for 1 prevents the error message.
trap {
    Write-Output "trap triggered on exception. Sleeping 1"
    Start-Sleep -Seconds 1
}

$prev_dir=$(Get-Location)

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Main Variables
[string]$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

#[string]$root = $PSScriptRoot
# [System.Uri]$gitUrl = "http://github.com/godotengine/godot-cpp.git"
[System.Uri]$gitUrl = "C:\Godot\src\godot-cpp"
#[string]$gitBranch = "modernise"
[string]$gitBranch = "modernise"

$platform="Windows"
$target="godot-cpp"

H2 " Build $target using $platform "
Write-Output "  platform    = $platform"
Write-Output "  target      = $target"
Write-Output "  root        = $root"

[string]$thisScript = $(Get-PSCallStack)[0].scriptName
Write-Output "  thisScript  = $thisScript"

# Get the target root from this script location
$targetRoot= $thisScript  | split-path -parent
Write-Output "  targetRoot  = $targetRoot"

cd "$targetRoot"

# Get script count
$buildScripts=@($(rg -u --files --max-depth 1) `
    | rg "$platform.*ps1" `
    | rg -v "build")

$scriptCount=$buildScripts.count
Write-Output "  Script count: $scriptCount"

#Fail if no scripts
if ( $scriptCount -eq 0 ) {
    cd "$prev_dir"
    Write-Error "No build scripts found"
    exit 1
}

# Print Scripts
Write-Output "  Scripts:"
foreach ( $script in $buildScripts ) {
    Write-Output "    $script"
}
Write-Output ""

# Make sure the log directories exist.
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-raw" | Out-Null
New-Item -Force -ItemType Directory -Path "$targetRoot/logs-clean" | Out-Null

# Some steps are identical.
function CommonPrep {

    # Clean up key artifacts to trigger rebuild
    [array]$artifacts = @($(rg -u --files "$buildRoot" `
        | rg "(memory|example).*?o(bj)?$" ))

    $artifacts += @($(rg -u --files "$buildRoot" `
        | rg "\.(a|lib|so|dll|dylib)$" ))

    #Ignore exit code from ripgrep failure to match files.
    $global:LASTEXITCODE = 0

    if( $artifacts.Length -gt 0 ){
        H3 "Removing key Artifacts"
        $artifacts | Foreach-Object -Parallel {
            Write-Host "Removing $_"
            Remove-Item $_
        }
    }
}

function CommonTest {
    $consoleDevice = if ($IsWindows) {
        '\\.\CON'
    } else {
        '/dev/tty'
    }

    H1 "Test"
    H3 "Generate the .godot folder"
    & $godot -e --path "$buildRoot\test\project" --quit --headless 2>&1 | Out-Host
    Start-Sleep -Seconds 1

    if( -Not (Test-Path "$buildRoot\test\project\.godot" -PathType Container) )
    {
        Get-Error
        write-Output "`$LASTEXITCODE = $LASTEXITCODE"
        write-Output "`$? = $?"
        write-Output "`$Error = $Error"
        return
    }
    
    H3 "Run the test project"
    $result = & $godot_tr --path "$buildRoot\test\project\" --quit --headless | Out-String

    Write-Output "`$result = $result"
    Write-Output "$result" | rg "PASSED"
}


function RunActions{
    Fetch 2>&1
    if( $LASTEXITCODE ){ Write-Error "Fetch-Failure" }
    CommonPrep 2>&1
    if( $LASTEXITCODE ){ Write-Error "Prep-Failure" }
    Build 2>&1
    if( $LASTEXITCODE ){ Write-Error "build-Failure" }
    CommonTest 2>&1 | Tee-Object -Append -FilePath  "$targetRoot\summary.log"
    if( $LASTEXITCODE ){ Write-Output "Test-Failure" }
    Clean 2>&1
    if( $LASTEXITCODE ){ Write-Output "Clean-Failure" }
}

# Process Scripts
foreach ( $script in $buildScripts ) {
    Write-Output "using $script ..."
#    trap {
#        "Script Failed: $script"
#        continue
#    }
    Set-Location $targetRoot

    $config= Split-Path -Path $script -LeafBase
    H2 "Processing - $config"

    $buildRoot="$targetRoot\$config"
    Write-Output "  buildRoot  = $buildRoot"

    $traceLog="$targetRoot\logs-raw\$config.txt"
    $cleanLog="$targetRoot\logs-clean\$config.txt"
    Write-Output "  traceLog   = $traceLog"
    Write-Output "  cleanLog   = $cleanLog"


    . "$root\share\build-actions.ps1"
    . "$targetRoot/$script"

#    try
#    {
        RunActions 2>&1 | Tee-Object -FilePath "$traceLog"
#    } catch {
#        H3 "Failure in: $config"
#        continue
#    }


    $matchPattern='(register_types|memory|libgdexample|libgodot-cpp)'
    rg -M2048 $matchPattern "$traceLog" | sed -E 's/ +/\n/g' `
        | sed -E ':a;$!N;s/(-(MT|MF|o)|\/D)\n/\1 /;ta;P;D' > "$cleanLog"

    H3 "Completed: $config"
}

cd $prev_dir


Start-Sleep -Seconds 1
