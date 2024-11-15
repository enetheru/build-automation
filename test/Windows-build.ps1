#!/usr/bin/env pwsh
#Requires -Version 7.4

H1 "Heading 1"

H2 "Heading 2"

H3 "Heading 3"

H2 "Fill"
Write-Output "Usage: Fill [fill_string] [width=\$COLUMNS]"

H3 "(Fill)"
Fill

H3 "(Fill =)"
Fill "="

H3 "(Fill '+' 40)"
Fill '+' 40

H3 "(Fill beans 20)"
Fill "beans" 20

H3 "(Fill '- ')"
Fill '- '

H2 "Center"
Write-Output "Usage: <inputLine> | Center [text] [lineOverride]"
Write-Output "  inputLine or LineOverride must be present, lineOverride takes precedence."

H3 'Fill "." | Center "Title"'
Fill "." | Center "Title"

H3 'Center "o.O"  "¯\_   _/¯"'
Center "o.O" "¯\_   _/¯"

H3 '(Center " Title " $(Fill "- ""))'
Center " Title " "$(Fill '- ')"


H2 "Right"
Write-Output "Usage: <line>|  Right [text] [lineOverride]"

H3 'Right "Right Alignment" "$(Fill "_")"'
Right "Right Alignment" "$(Fill "_")"

H3 'Fill "-" | Right " $(date ...) "'
Fill "-" | Right " $(date -format "%y-%m-%d") "


H2 "Mixed Use"

H3 "Fill - 20 | sed... "
Fill - 20 | sed -e "s/\(-\)-/\1=/g"

H3 " Fill - 60 | Center "
Fill - 60 | Center

H3 'Fill "- " | Center " Title " | Right " $(date ...) "'
Fill '- ' | Center " Title " | Right " $(date -format "%y-%m-%d") "

