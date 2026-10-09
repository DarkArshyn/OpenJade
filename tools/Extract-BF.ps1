#requires -Version 5.1
<#
.SYNOPSIS
    Extracts BF entries to a new directory and returns SHA-256 hashes.
.PARAMETER Path
    Path to the BF archive.
.PARAMETER Entry
    Exact internal filename to extract.
.PARAMETER All
    Extract every entry instead of selecting one.
.PARAMETER OutputDirectory
    New directory for extracted files; existing directories are refused.
.EXAMPLE
    .\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -Entry gamepads.dat -OutputDirectory .\reports\gamepads
#>
[CmdletBinding(DefaultParameterSetName='Single')]
param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory,ParameterSetName='Single')][string]$Entry,
    [Parameter(Mandatory,ParameterSetName='All')][switch]$All,
    [Parameter(Mandatory)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.BF.psm1') -Force
Export-OpenJadeBFEntry @PSBoundParameters
