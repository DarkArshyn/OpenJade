#requires -Version 5.1
<#
.SYNOPSIS
    Tests BIG v37 boundaries and optional local archive inspection.
.PARAMETER GameArchive
    Optional local prince.bf to inspect without modification.
#>
[CmdletBinding()]
param([string]$GameArchive)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.BIG.psm1')
$run=Join-Path $project ('reports/big-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name) {if(-not $Condition){throw "FAIL: $Name"};$checks.Add($Name)}
function Assert-Throws([scriptblock]$Action,[string]$Name) {$failed=$false;try{& $Action | Out-Null}catch{$failed=$true};Assert $failed $Name}
function Put([byte[]]$Bytes,[int]$Offset,[uint32]$Value) {[BitConverter]::GetBytes($Value).CopyTo($Bytes,$Offset)}
$fixture=Join-Path $run 'synthetic.bf'
$bytes=New-Object byte[] 400
([byte[]](66,73,71,0)).CopyTo($bytes,0)
Put $bytes 4 37;Put $bytes 8 2;Put $bytes 32 3;Put $bytes 36 1;Put $bytes 52 68
Put $bytes 68 300;Put $bytes 72 123
Put $bytes 76 396;Put $bytes 80 456
Put $bytes 300 3;$bytes[304]=1;$bytes[305]=2;$bytes[306]=3
Put $bytes 396 0
Put $bytes 92 3
[Text.Encoding]::ASCII.GetBytes('first.bin').CopyTo($bytes,112)
[Text.Encoding]::ASCII.GetBytes('empty.bin').CopyTo($bytes,196)
[IO.File]::WriteAllBytes($fixture,$bytes)
$before=(Get-FileHash $fixture).Hash
$a=Get-OpenJadeBIGIndex $fixture
Assert ($a.Summary.EntryCount -eq 2 -and $a.Summary.ValidRanges -eq 2) 'Two bounded entries'
Assert ($a.Entries[0].Id -eq 123 -and $a.Entries[0].PayloadOffset -eq 304 -and $a.Entries[0].EndOffset -eq 307) 'Independent ID and offset values'
Assert ($a.Entries[1].StoredLength -eq 0 -and $a.Entries[1].EndOffset -eq 400) 'Zero-length payload at EOF'
Assert ($a.Diagnostics.Count -eq 0) 'Valid fixture has no diagnostics'
Assert ($a.Summary.MetadataStart -eq 92 -and $a.Summary.Capacity -eq 3) 'Metadata uses capacity instead of active count'
Assert ($a.Entries[0].Name -ceq 'first.bin' -and $a.Entries[1].Name -ceq 'empty.bin') 'Ordinal ID-name associations'
Assert ($a.Summary.MatchingMetadataLengths -eq 2 -and $a.Summary.ValidNames -eq 2) 'Metadata lengths and names verified'
$output=Join-Path $run 'report'
Export-OpenJadeBIGReport $a $output | Out-Null
Assert (@(Import-Csv (Join-Path $output 'index.csv')).Count -eq 2) 'CSV index exported'
Assert ((Get-FileHash $fixture).Hash -eq $before) 'Input unchanged'
Assert-Throws {Export-OpenJadeBIGReport $a $output} 'Existing output refused'
Assert-Throws {Export-OpenJadeBIGReport $a (Join-Path $project 'game/forbidden')} 'Game output refused'
$bad=Join-Path $run 'bad.bf'
foreach($change in @(@{O=32;V=1;Code='MetadataLayoutUnavailable'},@{O=32;V=[uint32]::MaxValue;Code='MetadataLayoutUnavailable'},@{O=36;V=2;Code='MetadataLayoutUnavailable'},@{O=52;V=76;Code='MetadataLayoutUnavailable'},@{O=92;V=4;Code='MetadataLengthMismatch'},@{O=68;V=180;Code='MetadataPayloadOverlap'})) {
    $copy=[byte[]]$bytes.Clone();Put $copy $change.O $change.V;[IO.File]::WriteAllBytes($bad,$copy)
    $result=Get-OpenJadeBIGIndex $bad
    Assert (@($result.Diagnostics | Where-Object Code -eq $change.Code).Count -gt 0) "Metadata diagnostic: $($change.Code)"
}
$copy=[byte[]]$bytes.Clone();Put $copy 92 2147483651;Put $copy 104 42
[IO.File]::WriteAllBytes($bad,$copy);$flags=Get-OpenJadeBIGIndex $bad
Assert ($flags.Entries[0].MetadataSizeHighBit -and $flags.Entries[0].LengthMatches -and $flags.Entries[0].RecordUInt32At12 -eq 42) 'Size flag preserved separately and unknown word retained'
foreach($kind in @('Empty','NonAscii','ControlCharacter','Unterminated')) {
    $copy=[byte[]]$bytes.Clone()
    switch($kind){ 'Empty' {$copy[112]=0} 'NonAscii' {$copy[112]=233} 'ControlCharacter' {$copy[112]=9} 'Unterminated' {for($i=112;$i -lt 176;$i++){$copy[$i]=65}} }
    [IO.File]::WriteAllBytes($bad,$copy);$result=Get-OpenJadeBIGIndex $bad
    Assert ($result.Entries[0].NameStatus -eq $kind -and $result.Entries[0].Name -eq '' -and $result.Entries[0].NameRawHex.Length -gt 0) "Invalid name retained as raw bytes: $kind"
}
foreach($change in @(@{O=0;V=0},@{O=4;V=38},@{O=8;V=[uint32]::MaxValue})) {
    $copy=[byte[]]$bytes.Clone();Put $copy $change.O $change.V;[IO.File]::WriteAllBytes($bad,$copy)
    Assert-Throws {Get-OpenJadeBIGIndex $bad} 'Unsupported or oversized header refused'
}
[IO.File]::WriteAllBytes($bad,[byte[]](66,73,71,0))
Assert-Throws {Get-OpenJadeBIGIndex $bad} 'Truncated header refused'
foreach($change in @(@{O=68;V=0;Code='InvalidBlockOffset'},@{O=68;V=399;Code='InvalidBlockOffset'},@{O=300;V=[uint32]::MaxValue;Code='InvalidPayloadRange'},@{O=80;V=123;Code='DuplicateId'},@{O=76;V=300;Code='OverlappingBlock'})) {
    $copy=[byte[]]$bytes.Clone();Put $copy $change.O $change.V;[IO.File]::WriteAllBytes($bad,$copy)
    $result=Get-OpenJadeBIGIndex $bad
    Assert (@($result.Diagnostics | Where-Object Code -eq $change.Code).Count -gt 0) "Diagnostic: $($change.Code)"
}
$copy=[byte[]]$bytes.Clone();Put $copy 8 0;[IO.File]::WriteAllBytes($bad,$copy)
$empty=Get-OpenJadeBIGIndex $bad
Export-OpenJadeBIGReport $empty (Join-Path $run 'empty') | Out-Null
Assert ($empty.Entries.Count -eq 0 -and (Get-Content (Join-Path $run 'empty/index.csv')).StartsWith('"Index"')) 'Empty index report'
$command=& (Join-Path $project 'tools/Read-BIG.ps1') -Path $fixture
Assert ($command.Summary.SHA256 -eq $before) 'User command works'
$real=$null
if($GameArchive) {
    $before=(Get-FileHash -LiteralPath $GameArchive).Hash
    $result=Get-OpenJadeBIGIndex $GameArchive
    Assert ($result.Summary.EntryCount -gt 0) 'Real index is non-empty'
    Assert ($result.Summary.ValidRanges -eq $result.Summary.EntryCount) 'All real payload ranges fit'
    Assert ($result.Summary.ValidNames -eq $result.Summary.EntryCount) 'All real names valid'
    Assert ($result.Summary.MatchingMetadataLengths -eq $result.Summary.EntryCount) 'All real metadata lengths match block prefixes'
    Assert ((Get-FileHash -LiteralPath $GameArchive).Hash -eq $before -and $result.Summary.SHA256 -eq $before) 'Real archive unchanged'
    Export-OpenJadeBIGReport $result (Join-Path $run 'prince') | Out-Null
    $real=$result.Summary
}
[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray();RealArchive=$real} |
    ConvertTo-Json -Depth 4 | Set-Content (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
if($real){$real | Format-List}
