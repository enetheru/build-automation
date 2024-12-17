#!/usr/bin/env pwsh
#Requires -Version 7.4

# Powershell execution options
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

trap {
    Write-Output "Exception in Format.ps1"
    exit 1
}

# Check whether this file is sourced or not.
if( -Not ($MyInvocation.InvocationName -eq '.') ) {
    Write-Output "Do not run this script directly, it simply holds helper functions"
    exit 1
}
#FIXME, dont source this more than once. Add some guard.

# Update output buffer size to prevent clipping in Visual Studio output window.
if( $Host -and $Host.UI -and $Host.UI.RawUI ) {
    $rawUI = $Host.UI.RawUI
    #    $bufSize = $rawUI.BufferSize
    [int]$columns = $rawUI.BufferSize.Width
    #    $rows = $rawUI.BufferSize.height
    #    $typeName = $bufSize.GetType( ).FullName
    #    $newSize = New-Object $typeName (120, $rows)
    #    $rawUI.BufferSize = $newSize
} else {
    [int]$columns = 120
}

# Simplest to read from all the junk surrounding this question.
# https://stackoverflow.com/a/51268514
function DisplayInBytes()
{
    param(
        [int]$num
    )
    $suffix = "oct", "Kib", "Mib", "Gib", "Tib", "Pib", "Eib", "Zib", "Yib"
    $index = 0
    while ($num -gt 1kb)
    {
        $num = $num / 1kb
        $index++
    }
    
    $sFmt="{0:N"
    if ($index -eq 0) {$sFmt += "0"} else {$sFmt += "1"}
    $sFmt += "} {1}"
    $sFmt -f $num, $suffix[$index]
}

# If we dont have figlet then just replace it with something else
function Figlet {
    [CmdletBinding( PositionalBinding = $false )]
    param(
        [int]$width = $columns,
        [switch]$l,
        [switch]$c,
        [switch]$r,
        [string]$font="standard",
        [Parameter( ValueFromRemainingArguments = $true )]$message="Figlet is Cool"
    )
    $alignment="-l"
    foreach( $key in $PsBoundParameters.Keys ){
        switch( $key ) {
            "l" { $alignment="-l" }
            "c" { $alignment="-c" }
            "r" { $alignment="-r" }
        }
    }
    
    $customFiglet = "c:/git/cmatsuoka/figlet/figlet.exe"

    # other figlet fonts I like are 'standard','Ogre', 'Stronger Than All' and 'ANSI Regular'
    if( Get-Command $customFiglet -ErrorAction SilentlyContinue ) {
        # When I output text with figlet it inserts a completely useles character as the space.
        $q1 = [char] 0x2001  # [MQSP]
        
        &$customFiglet $alignment -w "$width" -f "$font" "$message" `
            | Where-Object { $_ -NotMatch "^\s*$" } `
            | ForEach-Object {
                if( $_.length -eq 0 ) { return }
                $_ -replace $q1, ' '
        }
    } else {
        Write-Output "==== $message ===="
    }
}

# Fill Command
function Fill {
    param(
        $filler = ' ',
        $width = $columns
    )
    [string]$line = "$filler"*$columns
    if( $line.Length -ge $width ) {
        $line = $line.Substring( 0, $width )
    }
    Write-Output "$line"
}

function Center {
    [CmdletBinding( )]
    param(
        [Parameter( Position = 0 )][string]$string = 'Center',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )

    process {
        [int]$length = $string.Length
        [int]$pos = ($line.Length - $string.Length) / 2
        if( $pos -lt 0 ) {
            Write-Output $string
        } else {
            $searchExp = "^(?<front>.{$pos}).{$length}(?<rear>.*$)"
            $replaceExp = "`${front}${string}`${rear}"
            $line -creplace $searchExp,$replaceExp
        }
    }
}

function Left {
    [CmdletBinding( )]
    param(
        [Parameter( Position = 0 )][string]$string = 'Left ',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )
    
    process {
        $pos = 0
        $length = $string.Length
        
        if( $pos -lt 0 ) {
            Write-Output $string
        } else {
            $searchExp = "^(?<front>.{$pos}).{$length}(?<rear>.*$)"
            $replaceExp = "`${front}${string}`${rear}"
            $line -creplace $searchExp,$replaceExp
        }
    }
}

function Right {
    [CmdletBinding( )]
    param(
        [Parameter( Position = 0 )][string]$string = ' Right',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )

    process {
        $pos = $line.Length - $string.Length - 1
        $length = $string.Length

        if( $pos -lt 0 ) {
            Write-Output $string
        } else {
            $searchExp = "^(?<front>.{$pos}).{$length}(?<rear>.*$)"
            $replaceExp = "`${front}${string}`${rear}"
            $line -creplace $searchExp,$replaceExp
        }
    }
}

##################################- Headings -##################################
#                                                                            #
#       ██   ██ ███████  █████  ██████  ██ ███    ██  ██████  ███████        #
#       ██   ██ ██      ██   ██ ██   ██ ██ ████   ██ ██       ██             #
#       ███████ █████   ███████ ██   ██ ██ ██ ██  ██ ██   ███ ███████        #
#       ██   ██ ██      ██   ██ ██   ██ ██ ██  ██ ██ ██    ██      ██        #
#       ██   ██ ███████ ██   ██ ██████  ██ ██   ████  ██████  ███████        #
#                                                                            #
################################################################################

function H1 {
    param(
        [Parameter( ValueFromRemainingArguments = $true )]$message
    )
    Figlet -c -f "big" $message
}

function H2 {
    param(
        [Parameter( ValueFromRemainingArguments = $true )]$args
    )
    #  printf "\n%s\n" "$(Center "- $1 -" "$(Fill "=")")"
    Write-Output "`n$(Fill "=" |  Center "- $args -")`n"
}

function H3 {
    param(
        [Parameter( ValueFromRemainingArguments = $true )]$args
    )
    Write-Output "`n == $args =="
}

function H4 {
    param(
        [Parameter( ValueFromRemainingArguments = $true )]$args
    )
    Write-Output "  => $args"
}

##################################- Command -###################################
#                                                                            #
#       ██████  ██████  ███    ███ ███    ███  █████  ███    ██ ██████       #
#      ██      ██    ██ ████  ████ ████  ████ ██   ██ ████   ██ ██   ██      #
#      ██      ██    ██ ██ ████ ██ ██ ████ ██ ███████ ██ ██  ██ ██   ██      #
#      ██      ██    ██ ██  ██  ██ ██  ██  ██ ██   ██ ██  ██ ██ ██   ██      #
#       ██████  ██████  ██      ██ ██      ██ ██   ██ ██   ████ ██████       #
#                                                                            #
################################################################################

function Format-Command {
    param(
        [Parameter( ValueFromRemainingArguments = $true )]$args
    )
    Write-Output ""
    Write-Output "  󰝰:$((get-location).Path)"
    Write-Output "  󰞷 $args"
}

function Format-Eval {
    Write-Output @"
  󰝰 $((get-location).Path)
  󰞷 $args
"@
    Invoke-Expression "$args"
}

function Print-Last-Error {
    H4 "last exit?     = $LASTEXITCODE"
    H4 "auto var `$?   = $?"
    H4 "Error?         = $Error"
}

##################################- Aggregate -#################################
#                                                                            #
# █████   ██████   ██████  ██████  ███████  ██████   █████  ████████ ███████ #
#██   ██ ██       ██       ██   ██ ██      ██       ██   ██    ██    ██      #
#███████ ██   ███ ██   ███ ██████  █████   ██   ███ ███████    ██    █████   #
#██   ██ ██    ██ ██    ██ ██   ██ ██      ██    ██ ██   ██    ██    ██      #
#██   ██  ██████   ██████  ██   ██ ███████  ██████  ██   ██    ██    ███████ #
#                                                                            #
################################################################################

function BigBox {
    Fill '#' | Center "- $args -"
    Right '#' | Left ' #'
    figlet -l -f "ANSI Regular" "$args" | ForEach-Object {
        Fill | Center $_ | Left ' #' | Right '#'
    }
    Right '#' | Left ' #'
    Fill '#'
}