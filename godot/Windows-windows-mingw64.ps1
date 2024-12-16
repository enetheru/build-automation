#!/usr/bin/env pwsh
#Requires -Version 7.4

# Configuration variables to pass to main build script.
param ( [switch] $c )
if( $c -eq $true ) {
    H4 "Using Default env Settings"
    return
}
