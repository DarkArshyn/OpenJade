#requires -Version 5.1
<#
.SYNOPSIS
    Decodes an extracted stored POP envelope into a new verified output directory.
.PARAMETER Path
    Stored payload from Extract-BIG.ps1, not a complete BF archive.
.PARAMETER OutputDirectory
    New directory outside game, containing stored, decoded, trailing and manifest files.
.PARAMETER MaxDecodedBytes
    Output allocation limit, at most 64 MiB. No silent truncation is performed.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$OutputDirectory,
    [ValidateRange(1,67108864)][int]$MaxDecodedBytes=67108864)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.POPLzo.psm1')
$root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
$game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
if($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'The game directory is read-only.'}
if(Test-Path -LiteralPath $root){throw 'Output directory already exists.'}
$ancestor=$root
while($ancestor){
    if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output path contains a reparse point.'}
    $ancestor=[IO.Path]::GetDirectoryName($ancestor)
}
$resolved=(Resolve-Path -LiteralPath $Path).ProviderPath
$stream=[IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
$reader=New-Object IO.BinaryReader($stream)
try {
    if($stream.Length -gt 67108864){throw 'Stored input exceeds the 64 MiB limit.'}
    $bytes=$reader.ReadBytes([int]$stream.Length)
    if($bytes.Length -ne $stream.Length){throw 'Truncated source read.'}
    $result=ConvertFrom-OpenJadePOPLzo -Bytes $bytes -MaxDecodedBytes $MaxDecodedBytes
    # Validate completely before creating output; I/O failure may leave partial files.
    [void][IO.Directory]::CreateDirectory($root)
    foreach($file in @(@{Name='source.stored.bin';Bytes=$bytes;Hash=$result.SourceSHA256},
        @{Name='decoded.bin';Bytes=$result.Bytes;Hash=$result.DecodedSHA256},
        @{Name='trailing.bin';Bytes=$result.TrailingBytes;Hash=$result.TrailingSHA256})){
        $target=Join-Path $root $file.Name
        $destination=[IO.File]::Open($target,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$destination.Write($file.Bytes,0,$file.Bytes.Length)}finally{$destination.Dispose()}
        if((Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash -cne $file.Hash){throw 'Output hash verification failed.'}
    }
    $manifest=[pscustomobject]@{SchemaVersion=1;CreatedAtUtc=[DateTime]::UtcNow.ToString('o');SourcePath=$resolved
        SourceLength=$bytes.Length;SourceSHA256=$result.SourceSHA256;DecodedLength=$result.Bytes.Length;DecodedSHA256=$result.DecodedSHA256
        ParsedLength=$result.ParsedLength;EndKind=$result.EndKind;TrailingLength=$result.TrailingBytes.Length;TrailingSHA256=$result.TrailingSHA256
        Blocks=$result.Blocks;OutputVerified=$true;ResourceSemanticsValidated=$false}
    $json=(New-Object Text.UTF8Encoding($false)).GetBytes(($manifest | ConvertTo-Json -Depth 5))
    $destination=[IO.File]::Open((Join-Path $root 'decoding.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$destination.Write($json,0,$json.Length)}finally{$destination.Dispose()}
    $manifest
}finally{$reader.Dispose()}
