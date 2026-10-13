#requires -Version 5.1
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'OpenJade.BIGCompression.psm1')
if (-not ('OpenJade.Lzo1x' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot 'OpenJade.Lzo1x.cs') }

function ConvertFrom-OpenJadePOPLzo {
    <#
    .SYNOPSIS
        Decodes a recognized POP envelope while preserving trailing bytes.
    .DESCRIPTION
        Supports classic LZO1X blocks and equal-size verbatim blocks only.
        Each compressed block must consume its complete input, end with the
        canonical marker and produce exactly the declared number of bytes.
        This is not an automatic decoder for arbitrary BIG entries.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][byte[]]$Bytes,
        [ValidateRange(1,67108864)][int]$MaxDecodedBytes=67108864)
    if($Bytes.Length -gt 67108864){throw 'Stored input exceeds the 64 MiB limit.'}
    $stream=New-Object IO.MemoryStream(,$Bytes)
    try {$probe=Get-OpenJadeBlockEnvelope $stream 0 $Bytes.Length} finally {$stream.Dispose()}
    if($probe.Status -ne 'BoundedCandidate'){throw 'Input is not a bounded supported POP envelope.'}
    if($probe.DeclaredDecodedLength -gt $MaxDecodedBytes){throw 'Declared output exceeds the configured limit.'}
    $output=New-Object byte[] ([int]$probe.DeclaredDecodedLength)
    $position=0
    $records=New-Object 'System.Collections.Generic.List[object]'
    foreach($block in $probe.Blocks){
        $stored=New-Object byte[] ([int]$block.StoredLength)
        [Array]::Copy($Bytes,[int]$block.DataOffset,$stored,0,$stored.Length)
        if($block.EqualSizes){$decoded=$stored;$method='Verbatim'}
        else {$decoded=[OpenJade.Lzo1x]::Decode($stored,[int]$block.DeclaredDecodedLength);$method='LZO1X'}
        [Array]::Copy($decoded,0,$output,$position,$decoded.Length)
        $records.Add([pscustomobject]@{Index=$block.Index;HeaderOffset=$block.HeaderOffset;DataOffset=$block.DataOffset
            StoredLength=$stored.Length;DecodedOffset=$position;DecodedLength=$decoded.Length;Method=$method
            StoredSHA256=(Get-OpenJadeByteHash $stored);DecodedSHA256=(Get-OpenJadeByteHash $decoded)})
        $position+=$decoded.Length
    }
    if($output.Length -lt 8 -or [BitConverter]::ToString($output,4,4) -cne $probe.MarkerHex){throw 'Decoded resource marker differs from candidate marker.'}
    $tail=New-Object byte[] ([int]$probe.RemainingLength)
    [Array]::Copy($Bytes,[int]$probe.ParsedLength,$tail,0,$tail.Length)
    [pscustomobject]@{Bytes=$output;TrailingBytes=$tail;Blocks=$records.ToArray();ParsedLength=$probe.ParsedLength
        EndKind=$probe.EndKind;SourceSHA256=(Get-OpenJadeByteHash $Bytes);DecodedSHA256=(Get-OpenJadeByteHash $output)
        TrailingSHA256=(Get-OpenJadeByteHash $tail)}
}

function Get-OpenJadeByteHash([byte[]]$Bytes){
    $sha=[Security.Cryptography.SHA256]::Create()
    try {[BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-','')}finally{$sha.Dispose()}
}

Export-ModuleMember -Function ConvertFrom-OpenJadePOPLzo
