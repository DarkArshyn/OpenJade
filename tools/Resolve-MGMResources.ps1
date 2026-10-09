#requires -Version 5.1
<#
.SYNOPSIS
    Links menu elements to local material/font declarations and resource files.
.PARAMETER Path
    Input MGM file.
.PARAMETER AssetRoot
    Extracted menu directory containing texture and fonts subdirectories.
.PARAMETER OutputDirectory
    Optional new directory for readable and CSV reports.
.EXAMPLE
    $links = .\tools\Resolve-MGMResources.ps1 -Path .\reports\data\menu\pop4common.mgm -AssetRoot .\reports\data\menu -OutputDirectory .\reports\common-links
    $links.Summary
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$AssetRoot,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MGMLinks.psm1')
$analysis=Get-OpenJadeMGMLinks -Path $Path -AssetRoot $AssetRoot
if ($OutputDirectory) {
    $report=Export-OpenJadeMGMLinks -Analysis $analysis -OutputDirectory $OutputDirectory
    Write-Host "Report: $($report.ReportPath)"
}
$analysis
