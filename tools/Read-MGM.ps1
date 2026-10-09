#requires -Version 5.1
<#
.SYNOPSIS
    Reads an MGM file and optionally writes structural reports.
.DESCRIPTION
    Returns a document with Summary, Bytes, Tags, Nodes, Materials and Diagnostics.
    No report is written unless OutputDirectory is supplied. The input is read-only.
.PARAMETER Path
    Input MGM file.
.PARAMETER OutputDirectory
    Optional new directory for summary, CSV tables, diagnostics and a readable tree.
.EXAMPLE
    $mgm = .\tools\Read-MGM.ps1 -Path .\reports\menu\pop4common.mgm
    $mgm.Summary
.EXAMPLE
    .\tools\Read-MGM.ps1 -Path .\reports\menu\pop4common.mgm -OutputDirectory .\reports\common-analysis
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MGM.psm1')
$document=Get-OpenJadeMGM -Path $Path
if ($OutputDirectory) {
    $report=Export-OpenJadeMGMReport -Document $document -OutputDirectory $OutputDirectory
    Write-Host "Report: $($report.ReportPath)"
}
$document
