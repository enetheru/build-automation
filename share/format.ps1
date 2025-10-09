#!/usr/bin/env pwsh
#Requires -Version 7.4

# Incase I forget here is the command for these banners:
# CodeBox -border "╭─╮│ │╰─╯" -compact -align left -font 'small' Message
# CodeBox -border "╒═╕│ │╘═╛" -compact -align left Message

# Fill '=' 64 | Left '# ' | Right '-' | Center "[ Message ]"

# Powershell execution options
Set-StrictMode -Version Latest

# THis enables unicode characters to show up in the console
$OutputEncoding = New-Object System.Text.UTF8Encoding
[console]::InputEncoding = $OutputEncoding
[console]::OutputEncoding = $OutputEncoding

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

# MARK: FORMAT
###################################- Format -###################################
#                                                                              #
#             ███████  ██████  ██████  ███    ███  █████  ████████             #
#             ██      ██    ██ ██   ██ ████  ████ ██   ██    ██                #
#             █████   ██    ██ ██████  ██ ████ ██ ███████    ██                #
#             ██      ██    ██ ██   ██ ██  ██  ██ ██   ██    ██                #
#             ██       ██████  ██   ██ ██      ██ ██   ██    ██                #
#                                                                              #
################################################################################

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
        [int]$indent = 0,
        [Parameter( Position = 0 )][string]$string = 'Left ',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )
    
    process {
        $pos = 0
        $length = $string.Length + $indent
        
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
        [int]$indent = 0,
        [Parameter( Position = 0 )][string]$string = ' Right',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )

    process {
        $pos = ($line.Length - $string.Length) - $indent
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


# USAGE:
# align -indent 4 -mode center "<string-to-align>" "<initial-string>"
function Align {
    [CmdletBinding( )]
    param(
        [int]$indent = 0,
        [string]$mode = 'center', # recognises [left, center, right] # TODO justified?
        [Parameter( Position = 0 )][string]$string = 'Alignment',
        [Parameter( Position = 1, ValueFromPipeline )][string]$line = "$(Fill)"
    )
    
    process {
        [int]$pos = 0
        switch($mode ){
            'left'   { $pos = $indent }
            'center' { $pos = (($line.Length - $string.Length) / 2) + $indent}
            'right'  { $pos = ($line.Length - $string.Length) - $indent }
        }
        [int]$length = $string.Length
        
        if( $pos -lt 0 ) {
            $pos = 0
        }
        $searchExp = "^(?<front>.{$pos}).{$length}(?<rear>.*$)"
        $replaceExp = "`${front}${string}`${rear}"
        $line -creplace $searchExp,$replaceExp
    }
}

# MARK: HEADING
##################################- Headings -##################################
#                                                                              #
#        ██   ██ ███████  █████  ██████  ██ ███    ██  ██████  ███████         #
#        ██   ██ ██      ██   ██ ██   ██ ██ ████   ██ ██       ██              #
#        ███████ █████   ███████ ██   ██ ██ ██ ██  ██ ██   ███ ███████         #
#        ██   ██ ██      ██   ██ ██   ██ ██ ██  ██ ██ ██    ██      ██         #
#        ██   ██ ███████ ██   ██ ██████  ██ ██   ████  ██████  ███████         #
#                                                                              #
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

# MARK: COMMAND
##################################- Command -###################################
#                                                                              #
#        ██████  ██████  ███    ███ ███    ███  █████  ███    ██ ██████        #
#       ██      ██    ██ ████  ████ ████  ████ ██   ██ ████   ██ ██   ██       #
#       ██      ██    ██ ██ ████ ██ ██ ████ ██ ███████ ██ ██  ██ ██   ██       #
#       ██      ██    ██ ██  ██  ██ ██  ██  ██ ██   ██ ██  ██ ██ ██   ██       #
#        ██████  ██████  ██      ██ ██      ██ ██   ██ ██   ████ ██████        #
#                                                                              #
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

# MARK: AGGREGATE
##################################- Aggregate -#################################
#                                                                              #
#  █████   ██████   ██████  ██████  ███████  ██████   █████  ████████ ███████  #
# ██   ██ ██       ██       ██   ██ ██      ██       ██   ██    ██    ██       #
# ███████ ██   ███ ██   ███ ██████  █████   ██   ███ ███████    ██    █████    #
# ██   ██ ██    ██ ██    ██ ██   ██ ██      ██    ██ ██   ██    ██    ██       #
# ██   ██  ██████   ██████  ██   ██ ███████  ██████  ██   ██    ██    ███████  #
#                                                                              #
################################################################################

function BigBox {
    [CmdletBinding( PositionalBinding = $false )]
    param(
        [string]$comment = '#',
        [string]$fill = '#',
        [int]$columns = 80,
        [Parameter( ValueFromRemainingArguments = $true )]$message
    )
    Fill $fill | Center "- $args -" | Left $comment
    Right '#' | Left '#'
    figlet -l -f "ANSI Regular" "$args" | ForEach-Object {
        Fill | Center $_ | Left ' #' | Right '#'
    }
    Right '#' | Left '#'
    Fill '#'
}

function CMakeH1 {
    $width=80
    if( ("$args".length % 2) -eq 1 ){
        $width = 79
    }
    Fill '=' $width | Left '#[' | Center "[ $args ]" | Right '] '
}

# MARK: CodeBox
# ╓────────────────────────────────────────────────────────────────────────────╖
# ║         ██████  ██████  ██████  ███████ ██████   ██████  ██   ██           ║
# ║        ██      ██    ██ ██   ██ ██      ██   ██ ██    ██  ██ ██            ║
# ║        ██      ██    ██ ██   ██ █████   ██████  ██    ██   ███             ║
# ║        ██      ██    ██ ██   ██ ██      ██   ██ ██    ██  ██ ██            ║
# ║         ██████  ██████  ██████  ███████ ██████   ██████  ██   ██           ║
# ╙────────────────────────────────────────────────────────────────────────────╜
# The above with:  CodeBox "CodeBox" -border "╓─╖║ ║╙─╜" -compact
[string]$codebox_help = '# CodeBox Help
# -h, --help    | show this help message
# -cols         | how many columns wide, default:-1 which is infinite
# -comment      | what to use as a comment starter, default:#
# -pad          | padding inside codebox
# -border       | nine characters describing border see below
# -compact      | reduce whitespace around text
# -above        | Title in top edge
# -below        | Title in bottom edge
# -font         | which figlet font to use
# -align        | align title within columns, (left, right, center)
# -mark         | insert a "MARK: <text>" ahead of box.
# <remaining text is interpreted as the title>
#
# Border:
# Support surrounding border | 012 | ╓─╖ | ╭─╮ | ▛▀▜
# and background             | 3B5 | ║ ║ | │ │ | ▌ ▐
# using nine characters.     | 678 | ╙─╜ | ╰─╯ | ▙▄▟
#
# Examples:
# "╓─╖║ ║╙─╜", "╔═╗║ ║╚═╝", "╭─╮│ │╰─╯", "▛▀▜▌ ▐▙▄▟",
# "┌─┐│ │└─┘", "┏━┓┃ ┃┗━┛", "╒═╕│ │╘═╛"
'

function CodeBox {
    [CmdletBinding( PositionalBinding = $false )]
    param(
        [Alias( "h" )][switch]$help,
        [Alias( "cols" )][int]$columns = -1,
        [string]$comment = '#',
        [string]$pad = ' ',
        [string]$border = "╒═╕│ │╘═╛",
        [switch]$compact,
        [string]$above,
        [string]$below,
        [string]$font = 'ANSI Regular',
        [string]$align = 'center',
        [switch]$mark,
        [Parameter( ValueFromRemainingArguments = $true )]$message = "Figlet Is Cool"
    )
    if( $help ){
        Write-Output $codebox_help
        return
    }

    # get the columns width from the figlet output.
    if( $columns -lt 0 ){
        $columns = 0;
        figlet -w 9001 -f "$font" ${message} | ForEach-Object {
            $_ | ForEach-Object {
                $length = $_.Length;
                if ($length -gt $columns) {
                    $columns = $length;
                }
            }
        };
        $columns = $columns + 1 + $comment.Length + $pad.Length + ($compact ? 0 : 4);

    } else {
        $columns = $columns - (($comment.Length + $pad.Length))
    }


    if( $border.Length -lt 9 ) {
        [string[]]$edges = ("$($border[0])" * 9).ToCharArray()
        $edges[4] = ' '
    } else {
        [string[]]$edges = $border.ToCharArray()
    }

    # Setup the left
#    if( -Not ($comment -eq $edges[3]) ){
#        0,3,6 | ForEach-Object { $edges[$_] = "${comment}${pad}$($edges[$_])" }
#    }

    # expand into rows without content
    $top = Fill -width $columns -filler $edges[1] | Left $edges[0] | Right $edges[2]
    $mid = Fill -width $columns -filler $edges[4] | Left $edges[3] | Right $edges[5]
    $bottom = Fill -width $columns -filler $edges[7] | Left $edges[6] | Right $edges[8]

    # Add the MARK
    if( $mark ) {
        "${comment}${pad}MARK: ${message}"
    }

    # Top Row
    "$comment$pad$($above ? ($top | Center "$above") : $top)"

    # Additional inside top
    $compact ? $null : "$comment$pad$mid"

    # if we are aligning to the left, then what column is the first inside the box?
    [int]$indent = 0
    if( $align -eq 'left') {
        $indent = $compact ? 1 : 3
    }

    # Create the figlet heading, and align inside middle rows.
    figlet -w $columns -l -f "$font" ${message} | ForEach-Object {
        "$comment$pad$($mid | Align -mode $align $_ -indent $indent)"
    }

    # Additional inside bottom
    $compact ? $null : "$comment$pad$mid"
    # Bottom Row
    "$comment$pad$($below ? ($bottom | Center "$below") : $bottom)"
}

# MARK: GODOT-HEADER
# Create a header for godot in the following style

$example = "
#                  ██████   ██████  ██████   ██████  ████████                  #
#                 ██       ██    ██ ██   ██ ██    ██    ██                     #
#                 ██   ███ ██    ██ ██   ██ ██    ██    ██                     #
#                 ██    ██ ██    ██ ██   ██ ██    ██    ██                     #
#                  ██████   ██████  ██████   ██████     ██                     #
func                        __________GODOT__________              ()->void:pass
"

function gdh {
    [CmdletBinding( PositionalBinding = $false )]
    param(
        [Alias( "h" )][switch]$help,
        [int]$cols = 80,
        [int]$outline_cols = 25,
        [string]$font = 'ANSI Regular',
        [string]$align = 'center',
        [Parameter( ValueFromRemainingArguments = $true )]$msg
    )
    if( $help ){
        Write-Output $example
        return
    }

    # Output figlet heading
    $mid = Fill -width $cols -filler ' ' | Left '#' | Right '#'
    figlet -l -f "$font" ${msg} | ForEach-Object {
        if( $align -eq "left"){
            $mid | Align -mode $align $_ -indent 2
        } else {
            $mid | Align -mode $align $_
        }
    }
    
    # Output func __heading__ for script panel outliner
    $func_name = Fill -width $outline_cols -filler '_' | Align ($msg.ToUpper() -replace '\W','_')

    $test = fill -width $cols -filler ' ' | Left 'func ' | Right '()->void:pass'
    Align $func_name $test

    # Write-Output "func $func_name()->void:pass"
}
