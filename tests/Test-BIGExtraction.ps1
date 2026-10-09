#requires -Version 5.1
<#
.SYNOPSIS
    Verifies stored BIG extraction using synthetic bytes and optional PC GOG data.
.PARAMETER GameArchive
    Optional local prince.bf; two selected payloads are compared with source bytes.
#>
[CmdletBinding()]
param([string]$GameArchive)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.BIG.psm1') -Force
$run=Join-Path $project ('reports/big-extraction-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name) {if(-not $Condition){throw "FAIL: $Name"};$checks.Add($Name)}
function Refuses([scriptblock]$Action,[string]$Name) {$failed=$false;try{& $Action | Out-Null}catch{$failed=$true};Assert $failed $Name}
function Put([byte[]]$Bytes,[int]$Offset,[uint32]$Value) {[BitConverter]::GetBytes($Value).CopyTo($Bytes,$Offset)}
function Hash([byte[]]$Bytes) {$sha=[Security.Cryptography.SHA256]::Create();try{[BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-','')}finally{$sha.Dispose()}}
$payload=New-Object byte[] 150003
for($i=0;$i -lt $payload.Length;$i++) {$payload[$i]=[byte]($i%251)}
$bytes=New-Object byte[] (300+4+$payload.Length+4)
([byte[]](66,73,71,0)).CopyTo($bytes,0)
Put $bytes 4 37;Put $bytes 8 2;Put $bytes 32 3;Put $bytes 36 1;Put $bytes 52 68
Put $bytes 68 300;Put $bytes 72 ([uint32]::MaxValue)
Put $bytes 76 ($bytes.Length-4);Put $bytes 80 123
Put $bytes 92 (2147483648L+$payload.Length)
[Text.Encoding]::ASCII.GetBytes('../escape.bin').CopyTo($bytes,112)
[Text.Encoding]::ASCII.GetBytes('empty.bin').CopyTo($bytes,196)
Put $bytes 300 $payload.Length;$payload.CopyTo($bytes,304)
$fixture=Join-Path $run 'synthetic.bf'
[IO.File]::WriteAllBytes($fixture,$bytes)
$before=(Get-FileHash $fixture).Hash
$result=& (Join-Path $project 'tools/Extract-BIG.ps1') -Path $fixture -Id '0xFFFFFFFF' -OutputDirectory (Join-Path $run 'hex')
$m=Get-Content -LiteralPath $result.ManifestPath -Raw | ConvertFrom-Json
Assert ($result.SHA256 -ceq (Hash $payload)) 'Multi-buffer output equals independent payload hash'
Assert ((Get-Item $result.OutputPath).Length -eq $payload.Length) 'Prefix excluded and exact stored length copied'
Assert ([IO.Path]::GetFileName($result.OutputPath) -ceq 'FFFFFFFF.stored.bin') 'ID filename ignores embedded traversal name'
Assert ($m.Name -ceq '../escape.bin' -and -not (Test-Path (Join-Path $run 'escape.bin'))) 'Original name retained only as metadata'
Assert ($m.Id -eq [uint32]::MaxValue -and $m.IdHex -ceq '0xFFFFFFFF') 'Unsigned high ID retained'
Assert ($m.BlockOffset -eq 300 -and $m.PayloadOffset -eq 304 -and $m.EndOffset -eq (304+$payload.Length)) 'Manifest source range exact'
Assert ($m.MetadataSizeHighBit -and $m.MetadataSizeRaw -eq (2147483648L+$payload.Length)) 'Raw metadata size flag retained'
Assert ($m.Verified -and -not $m.PrefixIncluded -and -not $m.Decompressed -and $m.Mode -ceq 'StoredPayload') 'Manifest describes stored copy only'
Assert ($m.ArchiveSHA256 -ceq $before -and $m.SourcePayloadSHA256 -ceq $m.OutputSHA256 -and $m.OutputSHA256 -ceq (Hash $payload)) 'Source archive and payload hashes recorded'
$decimal=Export-OpenJadeBIGEntry $fixture '4294967295' (Join-Path $run 'decimal')
Assert ($decimal.SHA256 -ceq $result.SHA256) 'Decimal ID selects same payload'
$empty=Export-OpenJadeBIGEntry $fixture '123' (Join-Path $run 'empty')
Assert ((Get-Item $empty.OutputPath).Length -eq 0 -and $empty.SHA256 -ceq (Hash ([byte[]]@()))) 'Empty payload at EOF extracted and hashed'
Refuses {Export-OpenJadeBIGEntry $fixture '123' (Join-Path $run 'hex')} 'Existing directory refused'
Assert ((Get-FileHash $result.OutputPath).Hash -ceq (Hash $payload)) 'Existing payload unchanged'
Refuses {Export-OpenJadeBIGEntry $fixture '123' (Join-Path $project 'game/forbidden')} 'Game output refused'
foreach($id in @('-1','0x100000000','4294967296','bad','0x','456')) {
    $out=Join-Path $run ('reject-'+[guid]::NewGuid().ToString('N'))
    Refuses {Export-OpenJadeBIGEntry $fixture $id $out} "Invalid or missing ID refused: $id"
    Assert (-not (Test-Path $out)) 'Rejected ID creates no output'
}
foreach($change in @(@{O=80;V=[uint32]::MaxValue},@{O=92;V=1},@{O=68;V=0},@{O=300;V=[uint32]::MaxValue},@{O=4;V=38})) {
    $copy=[byte[]]$bytes.Clone();Put $copy $change.O $change.V
    $bad=Join-Path $run 'bad.bf';[IO.File]::WriteAllBytes($bad,$copy)
    $out=Join-Path $run ('bad-'+[guid]::NewGuid().ToString('N'))
    Refuses {Export-OpenJadeBIGEntry $bad '0xFFFFFFFF' $out} "Ambiguous or invalid archive refused at $($change.O)"
    Assert (-not (Test-Path $out)) 'Rejected archive creates no output'
}
Assert ((Get-FileHash $fixture).Hash -ceq $before) 'Synthetic source unchanged'
$real=@()
if($GameArchive) {
    $before=(Get-FileHash -LiteralPath $GameArchive).Hash
    foreach($id in @('0x03090337','0xF402E7E7')) {
        $result=Export-OpenJadeBIGEntry $GameArchive $id (Join-Path $run $id)
        $m=Get-Content -LiteralPath $result.ManifestPath -Raw | ConvertFrom-Json
        $stream=[IO.File]::OpenRead((Resolve-Path -LiteralPath $GameArchive).ProviderPath)
        $reader=New-Object IO.BinaryReader($stream)
        try {$stream.Position=$m.PayloadOffset;$expected=$reader.ReadBytes([int]$m.StoredLength)}finally{$reader.Dispose()}
        Assert ($expected.Length -eq $m.StoredLength -and (Hash $expected) -ceq $result.SHA256) "Real output matches independently read source range: $id"
        Assert ($m.ArchiveSHA256 -ceq $before -and $m.Verified) "Real manifest verified: $id"
        $real+=$m
    }
    Assert ((Get-FileHash -LiteralPath $GameArchive).Hash -ceq $before) 'Real archive unchanged'
}
[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray();RealExtractions=$real} | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
