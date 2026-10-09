#requires -Version 5.1
<#
.SYNOPSIS
    Reports candidate block envelopes without decompressing or modifying data.
.PARAMETER Path
    Local BIG v37 archive.
.PARAMETER OutputDirectory
    Optional new report directory outside game data.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.BIGCompression.psm1')
if($OutputDirectory){
    $root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
    $game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
    if($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'The game directory is read-only.'}
    if(Test-Path -LiteralPath $root){throw 'Output directory already exists.'}
    $ancestor=$root
    while($ancestor){
        if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output path contains a reparse point.'}
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
    }
}
$result=Get-OpenJadeBIGCompression -Path $Path
if($OutputDirectory){
    [void][IO.Directory]::CreateDirectory($root)
    $result.Summary | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'summary.json') -Encoding UTF8
    $result.Entries | Export-Csv -LiteralPath (Join-Path $root 'entries.csv') -NoTypeInformation -Encoding UTF8
    $result.Blocks | Export-Csv -LiteralPath (Join-Path $root 'blocks.csv') -NoTypeInformation -Encoding UTF8
}
$result
