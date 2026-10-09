#requires -Version 5.1
<#
.SYNOPSIS
    Creates a text DAT from a Windows-1252 INI without changing its bytes.
.DESCRIPTION
    Save edited INI files as Windows-1252 without a BOM. This command does not
    transcode UTF-8, validate INI syntax or construct a binary DAT format.
    Output must be new and its parent directory must already exist.
.PARAMETER Path
    Source INI file, encoded as Windows-1252 without a BOM.
.PARAMETER Output
    New DAT file path.
.EXAMPLE
    .\tools\Convert-IniToDat.ps1 -Path .\reports\pop4pclocal.ini -Output .\reports\pop4pclocal-roundtrip.dat
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Output)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.TextDat.psm1') -Force
Convert-OpenJadeTextDat @PSBoundParameters
