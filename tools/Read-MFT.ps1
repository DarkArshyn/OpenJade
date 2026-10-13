#requires -Version 5.1
<# .SYNOPSIS
Inspects the observed PC GOG MFT layout and optionally exports its grayscale atlas.
.DESCRIPTION
Output preserves the full source, raw metric bytes, offsets and unknown fields.
The atlas is an inspection image; game alpha and text layout are not validated.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$Path,[string]$OutputDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MFT.psm1') -Force
$resolved=(Resolve-Path -LiteralPath $Path).ProviderPath
if((Get-Item -LiteralPath $resolved).Length -gt 16782464){throw 'MFT input exceeds supported size.'}
$bytes=[IO.File]::ReadAllBytes($resolved)
$font=Read-OpenJadeMFT -Bytes $bytes
$sha=[Security.Cryptography.SHA256]::Create()
try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','')}finally{$sha.Dispose()}
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
    Add-Type -AssemblyName System.Drawing
    [void][IO.Directory]::CreateDirectory($root)
    [IO.File]::WriteAllBytes((Join-Path $root 'source.mft'),$bytes)
    $font.Glyphs | Export-Csv (Join-Path $root 'glyphs.csv') -NoTypeInformation -Encoding UTF8
    $bitmap=New-Object Drawing.Bitmap($font.Width,$font.Height)
    try{
        for($y=0;$y -lt $font.Height;$y++){for($x=0;$x -lt $font.Width;$x++){
            $v=$font.Pixels[$y*$font.Width+$x]
            $bitmap.SetPixel($x,$y,[Drawing.Color]::FromArgb(255,$v,$v,$v))
        }}
        $bitmap.Save((Join-Path $root 'atlas.png'),[Drawing.Imaging.ImageFormat]::Png)
    }finally{$bitmap.Dispose()}
    [pscustomobject]@{SchemaVersion=1;SourcePath=$resolved;SourceSHA256=$hash;SourceLength=$bytes.Length
        Name=$font.Name;SizeWord=$font.SizeWord;HeaderWord=$font.HeaderWord;UnknownByte83=$font.UnknownByte83
        UnknownTailHex=$font.UnknownTailHex;Width=$font.Width;Height=$font.Height;PixelOffset=5248;GlyphCount=224
        AtlasInterpretation='Raw bytes mapped to opaque grayscale; alpha semantics unverified'
        AtlasSHA256=(Get-FileHash (Join-Path $root 'atlas.png')).Hash;GameTextLayoutValidated=$false
    } | ConvertTo-Json | Set-Content (Join-Path $root 'font.json') -Encoding UTF8
}
$font
