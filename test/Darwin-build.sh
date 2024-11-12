
H1 "Test"

H2 "Fill"

echo "Usage: Fill [fill_string] [width=\$COLUMNS]"

H3 "(Fill)"
Fill
H3 "(Fill =)"
Fill =
H3 "(Fill '+' 40)"
Fill '+' 40
H3 "(Fill beans 20)"
Fill beans 20
H3 "(Fill '- ')"
Fill '- '

H2 "Center"
echo "Usage: Center [Title] [Line]"
H3 "(Center)"
Center
H3 "(Center ' Title ')"
Center ' Title '
H3 '(Center " Title " $(Fill '-'))'
Center " Title " "$(Fill '-')"


H2 "Right"
echo "Usage: Right [text] [line]"
H3 "Right"
Right
H3 "Right \"Right Alignment\""
Right "Right Alignment"
H3 'Right "$(date ...)" "$(Fill)"'
Right "$(date +"%y-%m-%d")" "$(Fill)"


H2 "Mixed Use"

H2 " Center and Fill with Pipes "
H3 "Fill - 20 | sed... "
Fill - 20 | sed -E "s/(-)-/\1=/g"

H3 " Fill - 60 | Center "
Fill - 60 | Center

H3 "Center ' O.o ' <<<(Fill 'o-' 40)"
Center ' O.o ' <<<$(Fill 'o-' 20)

H3 'Fill "- " | Center " Title " | Right " $(date ...) "'
Fill '- ' | Center " Title " | Right " $(date +"%y-%m-%d") "
