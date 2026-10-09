#requires -Version 5.1
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'OpenJade.BIG.psm1')

function Get-OpenJadeBlockEnvelope {
    <#
    .SYNOPSIS
        Tests a bounded payload for a candidate POP block envelope; never decodes.
    .DESCRIPTION
        Hypothesis source: FulGerNet/pop-bf-lab lzo.py at revision
        76ac78a10751a08fda67e8d5f711171e6f2d9605. Independent structural probe.
        A marker is evidence for a candidate only, not proof of an LZO stream.
        Offsets returned by this function are relative to the supplied range.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][IO.Stream]$Stream,
        [Parameter(Mandatory)][long]$Offset,[Parameter(Mandatory)][long]$Length)
    if (-not $Stream.CanRead -or -not $Stream.CanSeek -or $Offset -lt 0 -or $Length -lt 0 -or $Offset -gt $Stream.Length -or $Length -gt $Stream.Length-$Offset) {throw 'Invalid readable source range.'}
    function Read-At([long]$Position,[int]$Count) {
        $Stream.Position=$Position
        $buffer=New-Object byte[] $Count
        $done=0
        while($done -lt $Count){$n=$Stream.Read($buffer,$done,$Count-$done);if($n -eq 0){throw 'Unexpected end of range.'};$done+=$n}
        return ,$buffer
    }
    $prefix=Read-At $Offset ([int][Math]::Min(32,$Length))
    $markerOffset=$null;$markerHex=''
    foreach($p in @(12,13,14)) {
        if($prefix.Length -ge $p+4 -and $prefix[$p] -eq 153 -and $prefix[$p+1] -eq 192 -and $prefix[$p+2] -eq 255 -and $prefix[$p+3] -in @(238,254)) {
            $markerOffset=$p;$markerHex=[BitConverter]::ToString($prefix,$p,4);break
        }
    }
    $blocks=New-Object 'System.Collections.Generic.List[object]'
    $status='NoRecognizedEnvelope';$reason='No supported marker at payload offsets 12, 13 or 14.'
    $cursor=0L;$decodedTotal=0L;$endKind='';$tailHex=''
    if($null -ne $markerOffset) {
        $status='InvalidCandidate';$reason='Candidate does not form a bounded block chain.'
        while($true) {
            if($Length-$cursor -lt 8){$reason='Missing block header or explicit terminator after a full block.';break}
            $header=Read-At ($Offset+$cursor) 8
            $decoded=[long][BitConverter]::ToUInt32($header,0)
            $stored=[long][BitConverter]::ToUInt32($header,4)
            if($decoded -eq 0 -and $stored -eq 0 -and $blocks.Count -gt 0){$cursor+=8;$endKind='ZeroPair';$status='BoundedCandidate';$reason='';break}
            if($decoded -lt 1 -or $decoded -gt 131072 -or $stored -lt 1){$reason='Unsupported or zero block size.';break}
            if($stored -gt $Length-$cursor-8){$reason='Block extends beyond the payload range.';break}
            if($blocks.Count -eq 0 -and $markerOffset+4 -gt 8+$stored){$reason='Marker is outside the first declared block.';break}
            if($blocks.Count -eq 0 -and (($markerOffset -eq 12 -and $decoded -ne $stored) -or ($markerOffset -ne 12 -and $decoded -le $stored))) {$reason='Initial marker position and size relation do not match the hypothesis.';break}
            $blocks.Add([pscustomobject]@{Index=$blocks.Count;HeaderOffset=$cursor;DataOffset=$cursor+8;StoredLength=$stored;DeclaredDecodedLength=$decoded;EqualSizes=($decoded -eq $stored)})
            $cursor+=8+$stored;$decodedTotal+=$decoded
            if($decoded -lt 131072){$endKind='ShortBlock';$status='BoundedCandidate';$reason='';break}
            if($cursor -eq $Length){$endKind='ExactBoundary';$status='BoundedCandidate';$reason='';break}
        }
        if($status -eq 'BoundedCandidate') {$tailHex=[BitConverter]::ToString((Read-At ($Offset+$cursor) ([int][Math]::Min(32,$Length-$cursor))))}
    }
    [pscustomobject]@{Status=$status;Reason=$reason;PrefixHex=[BitConverter]::ToString($prefix)
        MarkerOffset=$markerOffset;MarkerHex=$markerHex;BlockCount=$blocks.Count
        UnequalSizeBlocks=@($blocks | Where-Object {-not $_.EqualSizes}).Count
        DeclaredDecodedLength=$decodedTotal;ParsedLength=$cursor;RemainingLength=$Length-$cursor
        EndKind=$endKind;RemainingPrefixHex=$tailHex;CodecValidated=$false;Blocks=$blocks.ToArray()}
}

function Get-OpenJadeBIGCompression {
    <#
    .SYNOPSIS
        Inspects all indexed payloads for bounded POP compression candidates.
    .DESCRIPTION
        Reads prefixes and block headers only. Neither decompresses nor proves
        the absence of compression when the envelope is not recognized.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $resolved=(Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $stream=[IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $archive=Get-OpenJadeBIGIndex $resolved
        if($archive.Diagnostics.Count){throw 'Archive diagnostics must be investigated before compression inspection.'}
        $rows=New-Object 'System.Collections.Generic.List[object]'
        $blockRows=New-Object 'System.Collections.Generic.List[object]'
        foreach($entry in $archive.Entries) {
            $probe=Get-OpenJadeBlockEnvelope $stream $entry.PayloadOffset $entry.StoredLength
            $row=[ordered]@{Index=$entry.Index;IdHex=$entry.IdHex;Name=$entry.Name;PayloadOffset=$entry.PayloadOffset;StoredLength=$entry.StoredLength;MetadataSizeHighBit=$entry.MetadataSizeHighBit}
            foreach($property in $probe.PSObject.Properties){if($property.Name -ne 'Blocks'){$row[$property.Name]=$property.Value}}
            $rows.Add([pscustomobject]$row)
            foreach($block in $probe.Blocks){$blockRows.Add([pscustomobject]@{IdHex=$entry.IdHex;BlockIndex=$block.Index;HeaderOffset=$entry.PayloadOffset+$block.HeaderOffset;DataOffset=$entry.PayloadOffset+$block.DataOffset;StoredLength=$block.StoredLength;DeclaredDecodedLength=$block.DeclaredDecodedLength;EqualSizes=$block.EqualSizes})}
        }
        $summary=[pscustomobject]@{ArchiveSHA256=$archive.Summary.SHA256;EntryCount=$rows.Count
            BoundedCandidates=@($rows | Where-Object Status -eq BoundedCandidate).Count
            InvalidCandidates=@($rows | Where-Object Status -eq InvalidCandidate).Count
            Unrecognized=@($rows | Where-Object Status -eq NoRecognizedEnvelope).Count
            CodecValidated=$false}
        [pscustomobject]@{Summary=$summary;Entries=$rows.ToArray();Blocks=$blockRows.ToArray()}
    } finally {$stream.Dispose()}
}

Export-ModuleMember -Function Get-OpenJadeBlockEnvelope,Get-OpenJadeBIGCompression
