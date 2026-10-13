#requires -Version 5.1
<#
.SYNOPSIS
    Tests classic LZO1X and POP framing, optionally against official miniLZO.
.PARAMETER ReferenceDll
    Optional locally built miniLZO bridge with oracle_decode/oracle_compress exports.
.PARAMETER GameArchive
    Optional local PC GOG BIG archive; all recognized candidates are decoded.
#>
[CmdletBinding()]
param([string]$ReferenceDll,[string]$GameArchive)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.POPLzo.psm1') -Force
Import-Module (Join-Path $project 'src/OpenJade.BIGCompression.psm1')
$run=Join-Path $project ('reports/lzo-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name){if(-not $Condition){throw "FAIL: $Name"};$checks.Add($Name)}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action | Out-Null}catch{$failed=$true};Assert $failed $Name}
function Hash([byte[]]$Bytes){$sha=[Security.Cryptography.SHA256]::Create();try{[BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-','')}finally{$sha.Dispose()}}
function Put([byte[]]$Bytes,[int]$Offset,[uint32]$Value){[BitConverter]::GetBytes($Value).CopyTo($Bytes,$Offset)}
if($ReferenceDll){
    $dll=(Resolve-Path -LiteralPath $ReferenceDll).ProviderPath.Replace('"','""')
    Add-Type -TypeDefinition (@'
using System.Runtime.InteropServices;
public static class LzoOracle {
    [DllImport(@"DLLPATH", CallingConvention=CallingConvention.Cdecl)]
    public static extern int oracle_decode(byte[] input, int size, byte[] output, int capacity);
    [DllImport(@"DLLPATH", CallingConvention=CallingConvention.Cdecl)]
    public static extern int oracle_compress(byte[] input, int size, byte[] output, int capacity);
}
'@).Replace('DLLPATH',$dll)
}
function CheckVector([byte[]]$Encoded,[byte[]]$Expected,[string]$Name){
    $actual=[OpenJade.Lzo1x]::Decode($Encoded,$Expected.Length)
    Assert ((Hash $actual) -ceq (Hash $Expected)) $Name
    if($ReferenceDll){
        $reference=New-Object byte[] $Expected.Length
        $rc=[LzoOracle]::oracle_decode($Encoded,$Encoded.Length,$reference,$reference.Length)
        Assert ($rc -eq $Expected.Length -and (Hash $reference) -ceq (Hash $actual)) "miniLZO agrees: $Name"
    }
}
CheckVector ([byte[]](17,0,0)) ([byte[]]@()) 'Empty stream'
CheckVector ([byte[]](20,65,66,67,17,0,0)) ([byte[]](65,66,67)) 'Initial literals'
CheckVector ([byte[]](18,65,0,0,17,0,0)) ([byte[]](65,65,65)) 'Two-byte short match'
CheckVector ([byte[]](18,65,66,0,66,67,4,0,17,0,0)) ([byte[]](65,65,65,65,66,67,66,67)) 'Short match and trailing literal state'
$encoded=[byte[]](25,8,0,0,0,153,192,255,238,32,23,0,0,17,0,0)
$expected=New-Object byte[] 64
([byte[]](8,0,0,0,153,192,255,238)).CopyTo($expected,0)
for($i=8;$i -lt 64;$i++){$expected[$i]=238}
CheckVector $encoded $expected 'Extended overlapping match'
# Independently constructed long literal run followed by the state-4 match.
$literals=New-Object byte[] 2050
for($i=0;$i -lt $literals.Length;$i++){$literals[$i]=[byte]($i%251)}
$long=[byte[]](@(0,0,0,0,0,0,0,0,247)+$literals+@(0,0,17,0,0))
CheckVector $long ([byte[]]($literals+$literals[1..3])) 'Long literals and 2049-distance match'
foreach($distance in @(16385,49151)){
    $literalCount=$distance+5
    $prefix=New-Object 'System.Collections.Generic.List[byte]';$prefix.Add(0)
    $remaining=$literalCount-18
    while($remaining -gt 255){$prefix.Add(0);$remaining-=255}
    $prefix.Add([byte]$remaining)
    $data=New-Object byte[] $literalCount
    for($i=0;$i -lt $data.Length;$i++){$data[$i]=[byte]($i%251)}
    $instruction=if($distance -eq 16385){[byte[]](17,4,0)}else{[byte[]](25,252,255)}
    $packed=[byte[]]($prefix.ToArray()+$data+$instruction+@(17,0,0))
    CheckVector $packed ([byte[]]($data+$data[5..7])) "Long-distance match: $distance"
}
foreach($size in @(0,63,65,131073,-1)){Refuses {[OpenJade.Lzo1x]::Decode($encoded,$size)} "Wrong or excessive output size: $size"}
for($n=0;$n -lt $encoded.Length;$n++){
    $cut=New-Object byte[] $n;[Array]::Copy($encoded,$cut,$n)
    Refuses {[OpenJade.Lzo1x]::Decode($cut,64)} "Truncated stream at byte $n"
}
Refuses {[OpenJade.Lzo1x]::Decode([byte[]]($encoded+@(0)),64)} 'Bytes after end marker rejected'
Refuses {[OpenJade.Lzo1x]::Decode([byte[]](64,255,17,0,0),3)} 'Invalid back-reference rejected'
Refuses {[OpenJade.Lzo1x]::Decode([byte[]](18,65,18,0,0),1)} 'Noncanonical end marker rejected'
$wrapped=New-Object byte[] (8+$encoded.Length+3)
Put $wrapped 0 64;Put $wrapped 4 $encoded.Length;$encoded.CopyTo($wrapped,8)
$wrapped[$wrapped.Length-1]=42
$decoded=ConvertFrom-OpenJadePOPLzo $wrapped
Assert ((Hash $decoded.Bytes) -ceq (Hash $expected)) 'POP compressed envelope decoded'
Assert ($decoded.TrailingBytes.Length -eq 3 -and $decoded.TrailingBytes[2] -eq 42) 'Nonzero trailing bytes preserved'
Refuses {ConvertFrom-OpenJadePOPLzo $wrapped -MaxDecodedBytes 63} 'Envelope output limit enforced'
$raw=New-Object byte[] 28;Put $raw 0 20;Put $raw 4 20
([byte[]](8,0,0,0,153,192,255,238)).CopyTo($raw,8)
$rawResult=ConvertFrom-OpenJadePOPLzo $raw
Assert ($rawResult.Bytes.Length -eq 20 -and $rawResult.Blocks[0].Method -eq 'Verbatim') 'Equal-size block copied verbatim'
$multiple=New-Object byte[] (8+131072+8+20)
Put $multiple 0 131072;Put $multiple 4 131072
([byte[]](8,0,0,0,153,192,255,238)).CopyTo($multiple,8)
Put $multiple 131080 20;Put $multiple 131084 20
$multiResult=ConvertFrom-OpenJadePOPLzo $multiple
Assert ($multiResult.Blocks.Count -eq 2 -and $multiResult.Bytes.Length -eq 131092 -and $multiResult.TrailingBytes.Length -eq 0) 'Full then short verbatim blocks'
$fixture=Join-Path $run 'synthetic.stored.bin';[IO.File]::WriteAllBytes($fixture,$wrapped)
$before=Hash $wrapped;$out=Join-Path $run 'expanded'
$manifest=& (Join-Path $project 'tools/Expand-POPLzo.ps1') $fixture $out
Assert ((Get-FileHash (Join-Path $out 'source.stored.bin')).Hash -ceq $before -and (Get-FileHash $fixture).Hash -ceq $before) 'Stored original preserved'
Assert ($manifest.OutputVerified -and (Get-FileHash (Join-Path $out 'decoded.bin')).Hash -ceq (Hash $expected)) 'Decoded output verified'
Assert ((Get-Content (Join-Path $out 'decoding.json') -Raw | ConvertFrom-Json).TrailingLength -eq 3) 'Manifest written'
Refuses {& (Join-Path $project 'tools/Expand-POPLzo.ps1') $fixture $out} 'Existing output refused'
Refuses {& (Join-Path $project 'tools/Expand-POPLzo.ps1') $fixture (Join-Path $project 'game/forbidden')} 'Game output refused'
$bad=[byte[]]$wrapped.Clone();$bad[21]=0
[IO.File]::WriteAllBytes((Join-Path $run 'bad.bin'),$bad)
$badOut=Join-Path $run 'bad-output'
Refuses {& (Join-Path $project 'tools/Expand-POPLzo.ps1') (Join-Path $run 'bad.bin') $badOut} 'Invalid codec payload refused'
Assert (-not(Test-Path $badOut)) 'Failed decoding creates no output directory'
$differential=0
if($ReferenceDll){
    $random=New-Object Random 73517
    foreach($length in @(0,1,3,4,18,238,239,2049,16385,49153,131072)){
        foreach($kind in @('Random','Zero','Periodic')){
            $data=New-Object byte[] $length
            if($kind -eq 'Random'){$random.NextBytes($data)}
            if($kind -eq 'Periodic'){for($i=0;$i -lt $length;$i++){$data[$i]=[byte]($i%251)}}
            $buffer=New-Object byte[] ($length+[int]($length/16)+128)
            $n=[LzoOracle]::oracle_compress($data,$length,$buffer,$buffer.Length)
            if($n -lt 1){throw "Reference compression failed: $n"}
            $packed=New-Object byte[] $n;[Array]::Copy($buffer,$packed,$n)
            CheckVector $packed $data "Reference-compressed $kind/$length"
            $differential++
        }
    }
}
$real=New-Object 'System.Collections.Generic.List[object]'
$gameBlocks=0;$compressedBlocks=0;$verbatimBlocks=0;$archiveHash=$null
if($GameArchive){
    $archiveHash=(Get-FileHash -LiteralPath $GameArchive).Hash
    $index=Get-OpenJadeBIGCompression $GameArchive
    $stream=[IO.File]::OpenRead((Resolve-Path -LiteralPath $GameArchive).ProviderPath)
    $reader=New-Object IO.BinaryReader($stream)
    try {
        foreach($entry in @($index.Entries | Where-Object Status -eq BoundedCandidate)){
            $stream.Position=$entry.PayloadOffset;$stored=$reader.ReadBytes([int]$entry.StoredLength)
            $result=ConvertFrom-OpenJadePOPLzo $stored
            foreach($block in $result.Blocks){
                $gameBlocks++
                if($block.Method -eq 'Verbatim'){$verbatimBlocks++;continue}
                $compressedBlocks++
                if($ReferenceDll){
                    $packed=New-Object byte[] $block.StoredLength;[Array]::Copy($stored,[int]$block.DataOffset,$packed,0,$packed.Length)
                    $reference=New-Object byte[] $block.DecodedLength
                    $rc=[LzoOracle]::oracle_decode($packed,$packed.Length,$reference,$reference.Length)
                    if($rc -ne $reference.Length -or (Hash $reference) -cne $block.DecodedSHA256){throw "Reference mismatch: $($entry.IdHex), block $($block.Index), rc=$rc"}
                }
            }
            $real.Add([pscustomobject]@{IdHex=$entry.IdHex;Name=$entry.Name;SourceSHA256=$result.SourceSHA256;DecodedLength=$result.Bytes.Length;DecodedSHA256=$result.DecodedSHA256;Blocks=$result.Blocks.Count;TrailingLength=$result.TrailingBytes.Length;TrailingSHA256=$result.TrailingSHA256;ReferenceCompared=[bool]$ReferenceDll})
        }
    }finally{$reader.Dispose()}
    Assert ($real.Count -eq $index.Summary.BoundedCandidates -and $real.Count -gt 0) 'All real recognized candidates decoded'
    Assert ((Get-FileHash -LiteralPath $GameArchive).Hash -ceq $archiveHash) 'Real archive unchanged'
    $real | Export-Csv (Join-Path $run 'decoded-resources.csv') -NoTypeInformation -Encoding UTF8
}
$summary=[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray()
    DifferentialCases=$differential;ReferenceDllSHA256=$(if($ReferenceDll){(Get-FileHash $ReferenceDll).Hash}else{$null})
    ArchiveSHA256=$archiveHash;RealResources=$real.Count;RealBlocks=$gameBlocks;CompressedBlocks=$compressedBlocks;VerbatimBlocks=$verbatimBlocks;ReferenceCompared=[bool]$ReferenceDll}
$summary | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
$summary | Select-Object Checks,DifferentialCases,RealResources,RealBlocks,CompressedBlocks,VerbatimBlocks,ReferenceCompared | Format-List
