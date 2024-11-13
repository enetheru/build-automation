
H1 "Heading 1"

H2 "Heading 2"

H3 "Heading 3"

H2 "Fill"
echo "Usage: Fill [fill_string] [width=\$COLUMNS]"

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
echo "Usage: <inputLine> | Center [text] [lineOverride]"
echo "  inputLine or LineOverride must be present, lineOverride takes precedence."

H3 'Fill "." | Center "Title"'
Fill "." | Center "Title"

H3 'Center "o.O"  "¯\_   _/¯"'
Center "o.O" "¯\_   _/¯"

H3 '(Center " Title " $(Fill "- ""))'
Center " Title " "$(Fill '- ')"


H2 "Right"
echo "Usage: <line>|  Right [text] [lineOverride]"

H3 'Right "Right Alignment" "$(Fill "_")"'
Right "Right Alignment" "$(Fill "_")"

H3 'Fill "-" | Right " $(date ...) "'
Fill "-" | Right " $(date +"%y-%m-%d") "


H2 "Mixed Use"

H3 "Fill - 20 | sed... "
Fill - 20 | sed -E "s/(-)-/\1=/g"

H3 " Fill - 60 | Center "
Fill - 60 | Center

H3 "Center ' O.o ' <<<(Fill 'o-' 40)"
Center ' O.o ' <<<"$(Fill 'o-' 20)"

H3 'Fill "- " | Center " Title " | Right " $(date ...) "'
Fill '- ' | Center " Title " | Right " $(date +"%y-%m-%d") "

