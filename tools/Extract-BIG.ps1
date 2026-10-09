#requires -Version 5.1
<#
.SYNOPSIS
    Extracts a single stored BIG v37 payload by ID and writes its verification manifest.
.DESCRIPTION
    Input is read-only. No decompression is performed. Embedded names are kept
    in the manifest; the output filename is based on the numeric ID.
.PARAMETER Path
    Input prince.bf (PC GOG v37 layout), not POPData.BF.
.PARAMETER Id
    Unsigned decimal ID or quoted hexadecimal string, for example '0x03090337'.
.PARAMETER OutputDirectory
    New directory for the extracted payload and extraction.json.
.EXAMPLE
    .\tools\Extract-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -Id '0x03090337' -OutputDirectory .\reports\versiontag
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$Id,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.BIG.psm1')
Export-OpenJadeBIGEntry @PSBoundParameters
