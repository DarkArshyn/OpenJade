#requires -Version 7.6
<#
.SYNOPSIS
    Creates an experimental ASCII text specimen from an MFT atlas.
.DESCRIPTION
    Assumes signed horizontal/baseline bearings, unsigned advance and grayscale
    coverage. Crops the one-pixel border. No kerning, scaling or game styling.
    Preserves the input bytes and records each placement for comparison.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][string]$OutputDirectory,
    [ValidateLength(1,256)][string]$Text='Nouvelle partie',
    [ValidateRange(-16,32)][int]$ExtraSpacing=0
)
Set-StrictMode -Version 3.0
$ErrorActionPreference='Stop'
if($Text -match '[^\x20-\x7E]'){throw 'Only printable ASCII is supported; extended code mapping is unverified.'}
$separator = [IO.Path]::DirectorySeparatorChar
$root = [IO.Path]::TrimEndingDirectorySeparator([IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)))
$game = [IO.Path]::GetFullPath((Join-Path (Split-Path $PSScriptRoot -Parent) 'game'))
if ($root.Equals($game, [StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game + $separator, [StringComparison]::OrdinalIgnoreCase)) { throw 'The game directory is read-only.' }
if(Test-Path -LiteralPath $root){throw 'Output directory already exists.'}
$ancestor=$root
while($ancestor){
    if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output path contains a reparse point.'}
    $ancestor=[IO.Path]::GetDirectoryName($ancestor)
}
$resolved=(Resolve-Path -LiteralPath $Path).ProviderPath
if((Get-Item -LiteralPath $resolved).Length -gt 16782464){throw 'MFT input exceeds supported size.'}
$bytes=[IO.File]::ReadAllBytes($resolved)
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MFT.psm1') -Force
$font=Read-OpenJadeMFT $bytes
function SignedByte([int]$value){if($value -ge 128){return $value-256};return $value}
$pen=0;$minX=0;$maxX=0;$minY=0;$maxY=0
$placements=@(foreach($character in $Text.ToCharArray()){
    $g=$font.Glyphs[[int]$character-32]
    $x=$pen+(SignedByte $g.Metric2Raw);$y=-(SignedByte $g.Metric3Raw)
    $minX=[Math]::Min($minX,$x);$maxX=[Math]::Max($maxX,$x+$g.Width)
    $minY=[Math]::Min($minY,$y);$maxY=[Math]::Max($maxY,$y+$g.Height)
    [pscustomobject]@{Code=[int]$character;RecordOffset=$g.Offset;PenX=$pen;X=$x;Y=$y;Width=[int]$g.Width;Height=[int]$g.Height
        AtlasX=$g.AtlasX+1;AtlasY=$g.AtlasY+1;Advance=[int]$g.Metric4Raw}
    $pen+=[int]$g.Metric4Raw+$ExtraSpacing
    $minX=[Math]::Min($minX,$pen);$maxX=[Math]::Max($maxX,$pen)
})
$width=($maxX-$minX)+32;$height=($maxY-$minY)+32
if($width -gt 16384 -or $height -gt 1024){throw 'Specimen dimensions exceed supported bounds.'}
$originX=16-$minX;$baseline=16-$minY
if (-not ('OpenJade.Dds' -as [type])) { Add-Type -Path (Join-Path $PSScriptRoot '../src/OpenJade.Dds.cs') }

# Compose white glyphs into a transparent RGBA image.
$image = [OpenJade.DdsImage]::new()
$image.Width = $width
$image.Height = $height
$image.Rgba = [byte[]]::new($width * $height * 4)
foreach ($p in $placements) {
    for ($y = 0; $y -lt $p.Height; $y++) {
        for ($x = 0; $x -lt $p.Width; $x++) {
            $coverage = [int]$font.Pixels[($p.AtlasY + $y) * $font.Width + $p.AtlasX + $x]
            $dx = $originX + $p.X + $x
            $dy = $baseline + $p.Y + $y
            $offset = ($dy * $width + $dx) * 4
            $old = [int]$image.Rgba[$offset + 3]
            $alpha = [int][Math]::Round($coverage + $old * (255 - $coverage) / 255.0)
            $image.Rgba[$offset] = 255
            $image.Rgba[$offset + 1] = 255
            $image.Rgba[$offset + 2] = 255
            $image.Rgba[$offset + 3] = [byte]$alpha
        }
    }
}

[void][IO.Directory]::CreateDirectory($root)
[IO.File]::WriteAllBytes((Join-Path $root 'source.mft'), $bytes)
[OpenJade.Dds]::SavePng($image, (Join-Path $root 'text.png'), $false)

# The diagnostic image uses an opaque background and a baseline guide.
$preview = [OpenJade.DdsImage]::new()
$preview.Width = $width
$preview.Height = $height
$preview.Rgba = [byte[]]::new($width * $height * 4)
for ($y = 0; $y -lt $height; $y++) {
    if ($y -eq $baseline) {
        $r = 48
        $g = 100
        $b = 120
    } else {
        $r = 24
        $g = 28
        $b = 36
    }

    for ($x = 0; $x -lt $width; $x++) {
        $offset = ($y * $width + $x) * 4
        $alpha = [int]$image.Rgba[$offset + 3]
        $preview.Rgba[$offset] = [byte][Math]::Round((255 * $alpha + $r * (255 - $alpha)) / 255.0)
        $preview.Rgba[$offset + 1] = [byte][Math]::Round((255 * $alpha + $g * (255 - $alpha)) / 255.0)
        $preview.Rgba[$offset + 2] = [byte][Math]::Round((255 * $alpha + $b * (255 - $alpha)) / 255.0)
        $preview.Rgba[$offset + 3] = 255
    }
}
[OpenJade.Dds]::SavePng($preview, (Join-Path $root 'preview.png'), $false)
$placements | Export-Csv (Join-Path $root 'placements.csv') -NoTypeInformation -Encoding utf8NoBOM
$sha=[Security.Cryptography.SHA256]::Create()
try{$hash=[BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-','')}finally{$sha.Dispose()}
$manifest=[pscustomobject]@{SchemaVersion=1;SourcePath=$resolved;SourceSHA256=$hash;Text=$Text;FontName=$font.Name
    Width=$width;Height=$height;OriginX=$originX;Baseline=$baseline;ExtraSpacing=$ExtraSpacing
    Crop='AtlasX+1, AtlasY+1, Width, Height';HorizontalBearing='Metric2Raw interpreted as int8'
    BaselineBearing='Metric3Raw interpreted as int8; top = baseline - bearing'
    Advance='Metric4Raw interpreted as uint8';Coverage='Raw atlas byte used as white alpha; source-over blending'
    KerningApplied=$false;GameRenderingValidated=$false;TextPngSHA256=(Get-FileHash (Join-Path $root 'text.png')).Hash}
$manifest | ConvertTo-Json | Set-Content (Join-Path $root 'specimen.json') -Encoding utf8NoBOM
$manifest