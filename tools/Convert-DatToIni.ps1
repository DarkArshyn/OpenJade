#requires -Version 5.1
<#
.SYNOPSIS
    Creates an INI copy of a Windows-1252 text DAT without changing its bytes.
.DESCRIPTION
    Intended for text files such as pop4pclocal.dat, not binary DAT files.
    Output must be new and its parent directory must already exist.
.PARAMETER Path
    Source text DAT file, encoded as Windows-1252 without a BOM.
.PARAMETER Output
    New INI file path.
.EXAMPLE
    .\tools\Convert-DatToIni.ps1 -Path .\reports\pop4pclocal.dat -Output .\reports\pop4pclocal.ini
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Output)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.TextDat.psm1') -Force
Convert-OpenJadeTextDat @PSBoundParameters
