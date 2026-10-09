#requires -Version 5.1
<#
.SYNOPSIS
    Tests structural compression hypotheses, not codec correctness.
.PARAMETER GameArchive
    Optional local BIG v37 archive inspected read-only.
#>
[CmdletBinding()]
param([string]$GameArchive)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.BIGCompression.psm1') -Force
$run=Join-Path $project ('reports/big-compression-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name){if(-not $Condition){throw "FAIL: $Name"};$checks.Add($Name)}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action | Out-Null}catch{$failed=$true};Assert $failed $Name}
function Put([byte[]]$Bytes,[int]$Offset,[uint32]$Value){[BitConverter]::GetBytes($Value).CopyTo($Bytes,$Offset)}
function Probe([byte[]]$Bytes){$s=New-Object IO.MemoryStream(,$Bytes);try{Get-OpenJadeBlockEnvelope $s 0 $Bytes.Length}finally{$s.Dispose()}}
function Fixture([int]$Marker=13){$b=New-Object byte[] 36;Put $b 0 64;Put $b 4 20;([byte[]](153,192,255,238)).CopyTo($b,$Marker);return ,$b}
$b=Fixture
$p=Probe $b
Assert ($p.Status -eq 'BoundedCandidate' -and $p.BlockCount -eq 1) 'Single bounded candidate'
Assert ($p.ParsedLength -eq 28 -and $p.RemainingLength -eq 8 -and $p.EndKind -eq 'ShortBlock') 'Trailing bytes remain separate'
Assert ($p.DeclaredDecodedLength -eq 64 -and -not $p.CodecValidated) 'Declared size is not validated decoded data'
Assert ($p.Blocks[0].DataOffset -eq 8 -and $p.Blocks[0].StoredLength -eq 20) 'Block ranges retained'
$b[35]=42;$p=Probe $b
Assert ($p.RemainingPrefixHex.EndsWith('2A')) 'Nonzero trailing data retained without padding claim'
$b=Fixture 14;$b[17]=254;$p=Probe $b
Assert ($p.MarkerOffset -eq 14 -and $p.MarkerHex -eq '99-C0-FF-FE') 'Alternate marker and position detected'
$b=Fixture 12;Put $b 0 20;$p=Probe $b
Assert ($p.Status -eq 'BoundedCandidate' -and $p.UnequalSizeBlocks -eq 0) 'Equal-size envelope candidate'
$b=Fixture;Put $b 0 131072;Put $b 28 5;Put $b 32 5
$multi=New-Object byte[] 45;$b.CopyTo($multi,0);$p=Probe $multi
Assert ($p.Status -eq 'BoundedCandidate' -and $p.BlockCount -eq 2 -and $p.DeclaredDecodedLength -eq 131077) 'Full and short block chain'
Assert ($p.Blocks[1].HeaderOffset -eq 28 -and $p.ParsedLength -eq 41 -and $p.RemainingLength -eq 4) 'Second block offsets and trailing length'
$b=Fixture;Put $b 0 131072;$p=Probe $b
Assert ($p.EndKind -eq 'ZeroPair' -and $p.ParsedLength -eq 36) 'Explicit zero pair after full block'
$p=Probe ([byte[]]$b[0..27])
Assert ($p.EndKind -eq 'ExactBoundary' -and $p.RemainingLength -eq 0) 'Full block at exact boundary'
$p=Probe ([byte[]]$b[0..30])
Assert ($p.Status -eq 'InvalidCandidate') 'Partial following header rejected'
foreach($change in @(@{O=0;V=0},@{O=0;V=131073},@{O=4;V=0},@{O=4;V=1000},@{O=4;V=1},@{O=0;V=20})){
    $b=Fixture;Put $b $change.O $change.V;$p=Probe $b
    Assert ($p.Status -eq 'InvalidCandidate') "Invalid size or marker relation: $($change.O)/$($change.V)"
}
foreach($b in @((New-Object byte[] 0),(New-Object byte[] 7),(New-Object byte[] 40))){$p=Probe $b;Assert ($p.Status -eq 'NoRecognizedEnvelope') 'Unknown payload stays unknown'}
$b=Fixture;$outer=New-Object byte[] 50;$b.CopyTo($outer,5);$s=New-Object IO.MemoryStream(,$outer)
try {
    $p=Get-OpenJadeBlockEnvelope $s 5 36
    Assert ($p.Status -eq 'BoundedCandidate' -and $p.Blocks[0].DataOffset -eq 8) 'Nonzero source offset keeps relative block offsets'
    Refuses {Get-OpenJadeBlockEnvelope $s -1 1} 'Negative source offset rejected'
    Refuses {Get-OpenJadeBlockEnvelope $s 1 50} 'Range outside source rejected'
    Refuses {Get-OpenJadeBlockEnvelope $s 1 -1} 'Negative source length rejected'
}finally{$s.Dispose()}
$real=$null
if($GameArchive){
    $before=(Get-FileHash -LiteralPath $GameArchive).Hash
    $out=Join-Path $run 'prince'
    $real=& (Join-Path $project 'tools/Read-BIGCompression.ps1') -Path $GameArchive -OutputDirectory $out
    Assert ($real.Summary.EntryCount -eq $real.Entries.Count -and $real.Summary.EntryCount -gt 0) 'Every real indexed entry has an observation'
    Assert (($real.Summary.BoundedCandidates+$real.Summary.InvalidCandidates+$real.Summary.Unrecognized) -eq $real.Summary.EntryCount) 'Statuses partition real index'
    Assert (@($real.Entries | Where-Object {$_.CodecValidated}).Count -eq 0) 'No candidate falsely reported as codec validated'
    $valid=@($real.Entries | Where-Object Status -eq BoundedCandidate)
    Assert ($valid.Count -gt 0 -and @($valid | Where-Object {$_.ParsedLength+$_.RemainingLength -ne $_.StoredLength}).Count -eq 0) 'Candidate ranges account for full stored lengths'
    Assert (@(Import-Csv (Join-Path $out 'entries.csv')).Count -eq $real.Entries.Count) 'CSV observations exported'
    Assert (@(Import-Csv (Join-Path $out 'blocks.csv')).Count -eq $real.Blocks.Count) 'CSV block evidence exported'
    Refuses {& (Join-Path $project 'tools/Read-BIGCompression.ps1') $GameArchive $out} 'Existing output refused'
    Refuses {& (Join-Path $project 'tools/Read-BIGCompression.ps1') $GameArchive (Join-Path $project 'game/forbidden')} 'Game output refused'
    Assert ((Get-FileHash -LiteralPath $GameArchive).Hash -ceq $before -and $real.Summary.ArchiveSHA256 -ceq $before) 'Real archive unchanged'
}
[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray();Summary=$(if($real){$real.Summary}else{$null})} | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
if($real){$real.Summary | Format-List}
