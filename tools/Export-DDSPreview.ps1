#requires -Version 5.1
<#
.SYNOPSIS
    Decodes a legacy DXT1/DXT5 DDS into a transparent PNG and checkerboard preview.
.DESCRIPTION
    Supports one 2D surface and one mip level only. Preserves source bytes and
    records provenance. This previews texture pixels, not the game's rendering.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
if(-not ('OpenJade.Dds' -as [type])){Add-Type -Path (Join-Path $PSScriptRoot '../src/OpenJade.Dds.cs') -ReferencedAssemblies System.Drawing}
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
    if($stream.Length -gt 67108864){throw 'DDS input exceeds 64 MiB.'}
    $bytes=$reader.ReadBytes([int]$stream.Length)
    $image=[OpenJade.Dds]::Decode($bytes)
    $sha=[Security.Cryptography.SHA256]::Create()
    try {$sourceHash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','');$rgbaHash=[BitConverter]::ToString($sha.ComputeHash($image.Rgba)).Replace('-','')}finally{$sha.Dispose()}
    [void][IO.Directory]::CreateDirectory($root)
    $stored=Join-Path $root 'source.dds'
    $output=[IO.File]::Open($stored,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$output.Write($bytes,0,$bytes.Length)}finally{$output.Dispose()}
    if((Get-FileHash $stored).Hash -cne $sourceHash){throw 'Source copy mismatch.'}
    [OpenJade.Dds]::SavePng($image,(Join-Path $root 'texture.png'),$false)
    [OpenJade.Dds]::SavePng($image,(Join-Path $root 'preview.png'),$true)
    $manifest=[pscustomobject]@{SchemaVersion=1;SourcePath=$resolved;SourceSHA256=$sourceHash;SourceLength=$bytes.Length
        Width=$image.Width;Height=$image.Height;Format=$image.Format;HeaderFlags=$image.HeaderFlags;PixelFormatFlags=$image.PixelFormatFlags
        RawRgbBitCount=$image.RawRgbBitCount;RawMipCount=$image.RawMipCount;LinearSize=$image.LinearSize;DataOffset=128
        RgbaSHA256=$rgbaHash;TexturePngSHA256=(Get-FileHash (Join-Path $root 'texture.png')).Hash
        PreviewPngSHA256=(Get-FileHash (Join-Path $root 'preview.png')).Hash;PreviewBackground='16px checkerboard RGB 48/72'
        TextureColorTransformApplied=$false;GameRenderingValidated=$false}
    $json=(New-Object Text.UTF8Encoding($false)).GetBytes(($manifest | ConvertTo-Json))
    $output=[IO.File]::Open((Join-Path $root 'texture.json'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try{$output.Write($json,0,$json.Length)}finally{$output.Dispose()}
    $manifest
}finally{$reader.Dispose()}
