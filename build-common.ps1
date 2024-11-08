#!/usr/bin/env pwsh
#Requires -Version 7.4

param(
    $prefix='w64'
)

if( -Not $MyInvocation.InvocationName -eq '.' -or $MyInvocation.Line -eq ''){
    Write-Error "Do not run this script directly."
    exit
}

# Main Variables
[string]$godot="C:\build\godot\msvc.master\bin\godot.windows.editor.x86_64.exe"
[string]$godot_tr="C:\build\godot\msvc.master\bin\godot.windows.template_release.x86_64.exe"

# Process varargs for build configs.
if( $args ){
    $args = $args -split '\s+' -join '|'
    [string]$pattern = "^$prefix-(.*?)($args)(.*?)\.(ps1|sh)$"
    "Search command = rg -u --files --max-depth 1 | rg $pattern"
    [array]$buildConfigs = rg -u --files --max-depth 1 | rg $pattern `
        | ForEach-Object { Split-Path -LeafBase $_ }
} else{
    # scan the directory for configs.
    $buildConfigs = rg --files --max-depth 1 `
        | rg "$prefix(.*?)-(cmake|scons)-(.*?).(ps1|sh)$" `
        | ForEach-Object { Split-Path -LeafBase $_ }
}

# Quit if there are no configs.
if( -Not ($buildConfigs -is [array] -And $buildConfigs.count -gt 0) ) {
    if( $args ){ Write-Error "No configs found for: {$args}"
    } else { Write-Error "No Configs found in folder."  }
    exit 1
}

"== Build Configurations =="
$buildConfigs | Format-List -Property Name

function SourcePrep {
    param(
        [Parameter(Mandatory=$true)] [string]$buildRoot,
        [Parameter(Mandatory=$true)] [System.Uri]$sourceOrigin,
        $sourceBranch
    )
    Set-Location $root

    # Clone the repository
    if (-Not (Test-Path -Path $buildRoot -PathType Container))
    {
        git clone (${sourceBranch}?.Insert(0, "-b")) "$sourceOrigin" "$buildRoot"
    }

    # Change working directory
    Set-Location $buildRoot

    # Fetch any changes and reset to latest
    git fetch --all
    git reset --hard '@{u}'
    if ($sourceBranch)
    {
        git checkout $sourceBranch
    }

    #TODO fix when the tree diverges and needs to be clobbered.
}

Function Win2Unix {
    [CmdletBinding()]
    Param( [Parameter(ValueFromPipeline)] $Name )
    process { $Name -replace '\\','/' -replace ':','' -replace '^C','/c'  }
}