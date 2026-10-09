#requires -Version 5.1
<#
.SYNOPSIS
    Lists entries in a supported BF archive without modifying it.
.PARAMETER Path
    Path to the BF archive.
.EXAMPLE
    .\tools\Read-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.BF.psm1') -Force
(Get-OpenJadeBFArchive -Path $Path).Entries
