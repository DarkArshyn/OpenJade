#requires -Version 5.1
Set-StrictMode -Version Latest

function Get-OpenJadeBIGIndex {
    <#
    .SYNOPSIS
        Inspects the fixed header and numeric index of a little-endian BIG v37 file.
    .DESCRIPTION
        Reads only. Adds bounded v37 metadata and names; does not decode payloads.
        Layout reference: Swyter/poptools pop_prince_bf.bt, version 2023.01.30,
        commit c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8.
        Independently implemented for bounded inspection and diagnostics.
    .PARAMETER Path
        Input BIG v37 archive (for example prince.bf), not POPData.BF.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $resolved=(Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $stream=[IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $reader=New-Object IO.BinaryReader($stream)
    try {
        if ($stream.Length -lt 68) { throw 'Truncated BIG header: at least 68 bytes required.' }
        $header=$reader.ReadBytes(68)
        if ([BitConverter]::ToString($header,0,4) -cne '42-49-47-00') { throw 'Not a BIG archive. Use Read-BF for POPData.BF.' }
        $version=[BitConverter]::ToUInt32($header,4)
        if ($version -ne 37) { throw "Unsupported BIG version: $version. Only little-endian v37 is implemented." }
        $count=[BitConverter]::ToUInt32($header,8)
        $indexEnd=68L+8L*$count
        if ($indexEnd -gt $stream.Length) { throw 'BIG entry count exceeds the file bounds.' }
        $entries=New-Object 'System.Collections.Generic.List[object]'
        $issues=New-Object 'System.Collections.Generic.List[object]'
        $ids=New-Object 'System.Collections.Generic.HashSet[uint32]'
        for ($i=0;$i -lt $count;$i++) {
            $offset=[long]$reader.ReadUInt32(); $id=$reader.ReadUInt32()
            $entries.Add([pscustomobject][ordered]@{Index=$i;IndexOffset=68L+8L*$i;Id=$id;IdHex=('0x{0:X8}' -f $id)
                BlockOffset=$offset;PayloadOffset=$offset+4;StoredLength=$null;EndOffset=$null;BoundsValid=$false
                MetadataOffset=$null;Name='';NameStatus='Unavailable';NameRawHex=''
                MetadataSizeRaw=$null;MetadataSizeLow31=$null;MetadataSizeHighBit=$null;LengthMatches=$null
                RecordUInt32At4=$null;RecordUInt32At8=$null;RecordUInt32At12=$null;RecordUInt32At16=$null})
            if (-not $ids.Add($id)) { $issues.Add([pscustomobject]@{Code='DuplicateId';Index=$i;Offset=68L+8L*$i;Message='Numeric ID occurs more than once.'}) }
        }
        foreach ($entry in $entries) {
            if ($entry.BlockOffset -lt $indexEnd -or $entry.BlockOffset -gt $stream.Length-4) {
                $issues.Add([pscustomobject]@{Code='InvalidBlockOffset';Index=$entry.Index;Offset=$entry.BlockOffset;Message='Block prefix lies inside the header/index or outside the file.'})
                continue
            }
            $stream.Position=$entry.BlockOffset
            $entry.StoredLength=[long]$reader.ReadUInt32()
            $entry.EndOffset=$entry.PayloadOffset+$entry.StoredLength
            $entry.BoundsValid=$entry.StoredLength -le ($stream.Length-$entry.PayloadOffset)
            if (-not $entry.BoundsValid) { $issues.Add([pscustomobject]@{Code='InvalidPayloadRange';Index=$entry.Index;Offset=$entry.BlockOffset;Message='Declared payload extends beyond the file.'}) }
        }
        # This single-table v37 model is checked against the PC GOG dataset.
        # Capacity is distinct from the number of active entries. Metadata is
        # indexed by the same ordinal as offset/ID pairs, not by a guessed name.
        $capacity=[BitConverter]::ToUInt32($header,32)
        $tableCount=[BitConverter]::ToUInt32($header,36)
        $declaredIndexOffset=[BitConverter]::ToUInt32($header,52)
        $metadataStart=68L+8L*$capacity
        $metadataEnd=$metadataStart+84L*$count
        $metadataAvailable=$capacity -ge $count -and $tableCount -eq 1 -and
            $declaredIndexOffset -eq 68 -and $metadataEnd -le $stream.Length
        if (-not $metadataAvailable) {
            $issues.Add([pscustomobject]@{Code='MetadataLayoutUnavailable';Index=-1;Offset=32;Message='Capacity, descriptor or metadata range is outside the supported single-table model.'})
        } else {
            # Do not interpret payload bytes as metadata when ranges overlap.
            $overlap=@($entries | Where-Object { $_.BoundsValid -and $_.BlockOffset -lt $metadataEnd -and $_.EndOffset -gt $metadataStart }).Count -gt 0
            if ($overlap) {
                $metadataAvailable=$false
                $issues.Add([pscustomobject]@{Code='MetadataPayloadOverlap';Index=-1;Offset=$metadataStart;Message='Metadata overlaps an indexed block; names are withheld.'})
            }
        }
        if ($metadataAvailable) {
            foreach ($entry in $entries) {
                $entry.MetadataOffset=$metadataStart+84L*$entry.Index
                $stream.Position=$entry.MetadataOffset
                $raw=$reader.ReadBytes(84)
                $entry.MetadataSizeRaw=[BitConverter]::ToUInt32($raw,0)
                $entry.MetadataSizeLow31=[long]$entry.MetadataSizeRaw -band 2147483647L
                $entry.MetadataSizeHighBit=([long]$entry.MetadataSizeRaw -band 2147483648L) -ne 0
                foreach ($offset in @(4,8,12,16)) { $entry."RecordUInt32At$offset"=[BitConverter]::ToUInt32($raw,$offset) }
                if ($null -ne $entry.StoredLength) {
                    $entry.LengthMatches=$entry.MetadataSizeLow31 -eq $entry.StoredLength
                    if (-not $entry.LengthMatches) { $issues.Add([pscustomobject]@{Code='MetadataLengthMismatch';Index=$entry.Index;Offset=$entry.MetadataOffset;Message='Metadata low 31 bits differ from the block size prefix.'}) }
                }
                $entry.NameRawHex=[BitConverter]::ToString($raw,20,64)
                $nameBytes=[byte[]]$raw[20..83]
                $terminator=[Array]::IndexOf($nameBytes,[byte]0)
                $length=if ($terminator -lt 0) {64} else {$terminator}
                $nameStatus=if ($terminator -lt 0) {'Unterminated'} elseif ($length -eq 0) {'Empty'} else {'Valid'}
                for ($j=0;$j -lt $length;$j++) {
                    if ($nameBytes[$j] -gt 127) {$nameStatus='NonAscii';break}
                    if ($nameBytes[$j] -lt 32 -or $nameBytes[$j] -eq 127) {$nameStatus='ControlCharacter';break}
                }
                $entry.NameStatus=$nameStatus
                if ($nameStatus -eq 'Valid') { $entry.Name=[Text.Encoding]::ASCII.GetString($nameBytes,0,$length) }
                else { $issues.Add([pscustomobject]@{Code='InvalidMetadataName';Index=$entry.Index;Offset=$entry.MetadataOffset+20;Message="Name status: $nameStatus. Raw bytes retained; no replacement name invented."}) }
            }
        }
        $furthestEnd=-1L
        foreach ($entry in @($entries | Where-Object BoundsValid | Sort-Object BlockOffset,Index)) {
            if ($entry.BlockOffset -lt $furthestEnd) { $issues.Add([pscustomobject]@{Code='OverlappingBlock';Index=$entry.Index;Offset=$entry.BlockOffset;Message='Block overlaps another indexed block; interpretation not established.'}) }
            $furthestEnd=[Math]::Max($furthestEnd,[long]$entry.EndOffset)
        }
        $fields=@(for($offset=4;$offset -lt 68;$offset+=4) {
            [pscustomobject]@{Offset=$offset;UInt32=[BitConverter]::ToUInt32($header,$offset)}
        })
        $stream.Position=0
        $hash=[Security.Cryptography.SHA256]::Create()
        try { $sha=[BitConverter]::ToString($hash.ComputeHash($stream)).Replace('-','') }
        finally { $hash.Dispose() }
        $summary=[pscustomobject]@{FileName=[IO.Path]::GetFileName($resolved);FileSize=$stream.Length;SHA256=$sha;Version=$version
            EntryCount=$entries.Count;IndexOffset=68;IndexEndOffset=$indexEnd
            ValidRanges=@($entries | Where-Object BoundsValid).Count;DiagnosticCount=$issues.Count
            Capacity=$capacity;MetadataAvailable=$metadataAvailable;MetadataStart=$metadataStart;MetadataEnd=$metadataEnd
            ValidNames=@($entries | Where-Object NameStatus -eq Valid).Count
            MatchingMetadataLengths=@($entries | Where-Object LengthMatches -eq $true).Count}
        [pscustomobject]@{Path=$resolved;Summary=$summary;HeaderHex=[BitConverter]::ToString($header)
            HeaderFields=$fields;Entries=$entries.ToArray();Diagnostics=$issues.ToArray()}
    } finally { $reader.Dispose() }
}

function Export-OpenJadeBIGReport {
    <#
    .SYNOPSIS
        Writes index.csv, header-fields.csv, summary.json and diagnostics.json.
    .PARAMETER Archive
        Result of Get-OpenJadeBIGIndex.
    .PARAMETER OutputDirectory
        New directory for reports. Existing roots and game output are refused.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][psobject]$Archive,[Parameter(Mandatory)][string]$OutputDirectory)
    $root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
    $game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
    if ($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)) {throw 'The game directory is read-only.'}
    if(Test-Path -LiteralPath $root) {throw 'Report directory already exists.'}
    $ancestor=$root
    while($ancestor) {
        if(Test-Path -LiteralPath $ancestor) {
            if(((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {throw 'Report path contains a reparse point.'}
        }
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
    }
    [void][IO.Directory]::CreateDirectory($root)
    $utf8=New-Object Text.UTF8Encoding($false)
    [IO.File]::WriteAllText((Join-Path $root 'summary.json'),($Archive.Summary | ConvertTo-Json),$utf8)
    [IO.File]::WriteAllText((Join-Path $root 'diagnostics.json'),(ConvertTo-Json -InputObject @($Archive.Diagnostics)),$utf8)
    [IO.File]::WriteAllText((Join-Path $root 'header-hex.txt'),$Archive.HeaderHex,$utf8)
    $Archive.HeaderFields | Export-Csv -LiteralPath (Join-Path $root 'header-fields.csv') -NoTypeInformation -Encoding UTF8
    if ($Archive.Entries.Count) { $Archive.Entries | Export-Csv -LiteralPath (Join-Path $root 'index.csv') -NoTypeInformation -Encoding UTF8 }
    else { [IO.File]::WriteAllText((Join-Path $root 'index.csv'),'"Index","IndexOffset","Id","IdHex","BlockOffset","PayloadOffset","StoredLength","EndOffset","BoundsValid","MetadataOffset","Name","NameStatus","NameRawHex","MetadataSizeRaw","MetadataSizeLow31","MetadataSizeHighBit","LengthMatches","RecordUInt32At4","RecordUInt32At8","RecordUInt32At12","RecordUInt32At16"'+"`r`n",$utf8) }
    [pscustomobject]@{OutputDirectory=$root;IndexPath=(Join-Path $root 'index.csv')}
}

function Export-OpenJadeBIGEntry {
    <#
    .SYNOPSIS
        Extracts one BIG v37 stored payload by unsigned numeric ID.
    .DESCRIPTION
        Copies exactly StoredLength bytes starting at PayloadOffset, excluding
        the four-byte block prefix. No decompression, decoding or repacking.
        Uses an ID-based output filename; embedded names are metadata only.
        Refuses ambiguous IDs, archive diagnostics and existing output roots.
        I/O failure may leave partial output; a manifest is written only after
        the extracted file hash matches the source payload hash.
    .PARAMETER Path
        Input BIG v37 archive.
    .PARAMETER Id
        Unsigned decimal ID or quoted hexadecimal string such as '0x03090337'.
    .PARAMETER OutputDirectory
        New directory for the stored payload and extraction.json manifest.
    .EXAMPLE
        Export-OpenJadeBIGEntry -Path .\game\TSoT-GOG\prince.bf -Id '0x03090337' -OutputDirectory .\reports\versiontag
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$Id,
        [Parameter(Mandatory)][string]$OutputDirectory)
    $numericId=[uint32]0
    if ($Id -cmatch '^0[xX][0-9a-fA-F]{1,8}$') {
        $numericId=[uint32]::Parse($Id.Substring(2),[Globalization.NumberStyles]::AllowHexSpecifier,[Globalization.CultureInfo]::InvariantCulture)
    } elseif ($Id -cmatch '^[0-9]+$') {
        if (-not [uint32]::TryParse($Id,[ref]$numericId)) { throw 'ID is outside the UInt32 range.' }
    } else { throw 'Use an unsigned decimal ID or a quoted hexadecimal ID (0x00000000 through 0xFFFFFFFF).' }
    $root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
    $game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
    if ($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'The game directory is read-only.' }
    if (Test-Path -LiteralPath $root) { throw 'Output directory already exists.' }
    $ancestor=$root
    while ($ancestor) {
        if (Test-Path -LiteralPath $ancestor) {
            if (((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Output path contains a reparse point.' }
        }
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
    }
    $resolved=(Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    # Keep a read-only handle open across indexing, hashing and copying. On the
    # Windows baseline this prevents concurrent write/delete access to the file.
    $source=[IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    try {
        $archive=Get-OpenJadeBIGIndex -Path $resolved
        $matches=@($archive.Entries | Where-Object { $_.Id -eq $numericId })
        if ($matches.Count -ne 1) { throw "Expected exactly one matching ID; found $($matches.Count)." }
        if ($archive.Diagnostics.Count) { throw 'Archive diagnostics must be investigated before extraction.' }
        $entry=$matches[0]
        if (-not $entry.BoundsValid -or -not $entry.LengthMatches) { throw 'Selected range is not validated.' }
        [void][IO.Directory]::CreateDirectory($root)
        $output=Join-Path $root ('{0:X8}.stored.bin' -f $numericId)
        $destination=[IO.File]::Open($output,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        $sha=[Security.Cryptography.SHA256]::Create()
        try {
            $source.Position=$entry.PayloadOffset
            $remaining=[long]$entry.StoredLength
            $buffer=New-Object byte[] 65536
            while ($remaining -gt 0) {
                $read=$source.Read($buffer,0,[int][Math]::Min($buffer.Length,$remaining))
                if ($read -eq 0) { throw 'Unexpected end of source payload.' }
                [void]$sha.TransformBlock($buffer,0,$read,$buffer,0)
                $destination.Write($buffer,0,$read)
                $remaining-=$read
            }
            [void]$sha.TransformFinalBlock([byte[]]@(),0,0)
            $payloadHash=[BitConverter]::ToString($sha.Hash).Replace('-','')
        } finally { $destination.Dispose(); $sha.Dispose() }
        $outputHash=(Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash
        if ($outputHash -cne $payloadHash -or (Get-Item -LiteralPath $output).Length -ne $entry.StoredLength) { throw 'Extracted payload verification failed.' }
        $manifest=[pscustomobject][ordered]@{
            SchemaVersion=1;Mode='StoredPayload';ExtractedAtUtc=[DateTime]::UtcNow.ToString('o')
            ArchivePath=$resolved;ArchiveSHA256=$archive.Summary.SHA256;ArchiveVersion=$archive.Summary.Version
            Index=$entry.Index;Id=$entry.Id;IdHex=$entry.IdHex;Name=$entry.Name;NameStatus=$entry.NameStatus
            BlockOffset=$entry.BlockOffset;PayloadOffset=$entry.PayloadOffset;StoredLength=$entry.StoredLength;EndOffset=$entry.EndOffset
            MetadataOffset=$entry.MetadataOffset;MetadataSizeRaw=$entry.MetadataSizeRaw;MetadataSizeHighBit=$entry.MetadataSizeHighBit
            PrefixIncluded=$false;Decompressed=$false;OutputFile=[IO.Path]::GetFileName($output)
            SourcePayloadSHA256=$payloadHash;OutputSHA256=$outputHash;Verified=$true
        }
        $manifestPath=Join-Path $root 'extraction.json'
        $json=$manifest | ConvertTo-Json -Depth 3
        $manifestStream=[IO.File]::Open($manifestPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {
            $jsonBytes=(New-Object Text.UTF8Encoding($false)).GetBytes($json)
            $manifestStream.Write($jsonBytes,0,$jsonBytes.Length)
        } finally { $manifestStream.Dispose() }
        [pscustomobject]@{IdHex=$entry.IdHex;Name=$entry.Name;Length=$entry.StoredLength;OutputPath=$output;ManifestPath=$manifestPath;SHA256=$outputHash}
    } finally { $source.Dispose() }
}

Export-ModuleMember -Function Get-OpenJadeBIGIndex,Export-OpenJadeBIGReport,Export-OpenJadeBIGEntry
