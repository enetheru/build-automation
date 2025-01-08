#!/usr/bin/env pwsh
#Requires -Version 7.4

######################    Setup PowerShell Preferences    #####################
# https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables?view=powershell-7.4
Set-StrictMode -Version Latest

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

# THis enables unicode characters to show up in the console
$OutputEncoding = New-Object System.Text.UTF8Encoding
[console]::InputEncoding = $OutputEncoding
[console]::OutputEncoding = $OutputEncoding

"calling: python build.py $args"
python build.py $args