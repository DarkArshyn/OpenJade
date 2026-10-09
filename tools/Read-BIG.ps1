#requires -Version 5.1
<#
.SYNOPSIS
    Inspects BIG v37 resource IDs, names and metadata without extracting data.
.PARAMETER Path
    Input prince.bf file. POPData.BF uses a different format and Read-BF.ps1.
.PARAMETER OutputDirectory
    Optional new directory for index and diagnostic reports.
.EXAMPLE
    $big = .\tools\Read-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -OutputDirectory .\reports\prince-index
    $big.Summary
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.BIG.psm1')
$archive=Get-OpenJadeBIGIndex -Path $Path
if($OutputDirectory) { Export-OpenJadeBIGReport -Archive $archive -OutputDirectory $OutputDirectory | Out-Host }
$archive
