#requires -Version 7.6
param([string]$FontDirectory)
Set-StrictMode -Version 3.0
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MFT.psm1') -Force
$script:checks=0
function Assert($condition,$message){if(-not $condition){throw $message};$script:checks++}
function Read-PngRgba([string]$Path) {
    $bytes = [IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 33 -or [BitConverter]::ToString($bytes, 0, 8) -ne '89-50-4E-47-0D-0A-1A-0A') { throw 'Invalid PNG signature.' }
    $stream = [IO.MemoryStream]::new($bytes)
    $reader = [IO.BinaryReader]::new($stream)
    $idat = [IO.MemoryStream]::new()
    try {
        $stream.Position = 8
        $width = 0
        $height = 0
        $hasHeader = $false
        $hasEnd = $false
        while ($stream.Position -lt $stream.Length) {
            $lengthBytes = $reader.ReadBytes(4)
            if ($lengthBytes.Length -ne 4) { throw 'Truncated PNG chunk length.' }
            [long]$length = (
                [long]$lengthBytes[0] * 16777216 +
                [long]$lengthBytes[1] * 65536 +
                [long]$lengthBytes[2] * 256 +
                [long]$lengthBytes[3]
            )
            if ($length -gt ($stream.Length - $stream.Position - 8) -or $length -gt [int]::MaxValue) { throw 'Invalid PNG chunk length.' }
            $type = [Text.Encoding]::ASCII.GetString($reader.ReadBytes(4))
            $data = $reader.ReadBytes([int]$length)
            # Skip the chunk CRC.
            [void]$reader.ReadBytes(4)
            switch -CaseSensitive ($type) {
                'IHDR' { 
                    if ($hasHeader -or $data.Length -ne 13) { throw 'Invalid PNG header.' }
                    $width = (
                        [long]$data[0] * 16777216 +
                        [long]$data[1] * 65536 +
                        [long]$data[2] * 256 +
                        [long]$data[3]
                    )
                    $height = (
                        [long]$data[4] * 16777216 +
                        [long]$data[5] * 65536 +
                        [long]$data[6] * 256 +
                        [long]$data[7]
                    )
                    if ($width -lt 1 -or $height -lt 1 -or
                        $width -gt 8192 -or $height -gt 8192 -or
                        ($width * $height) -gt 16777216 -or
                        $data[8] -ne 8 -or
                        $data[9] -ne 6 -or
                        $data[10] -ne 0 -or
                        $data[11] -ne 0 -or
                        $data[12] -ne 0) { throw 'Unsupported PNG format.' }
                    $hasHeader = $true
                }
                'IDAT' {$idat.Write($data, 0, $data.Length)}
                'IEND' { 
                    if ($data.Length -ne 0) { throw 'Invalid PNG end chunk.' }
                    $hasEnd = $true
                }
            }
            if ($hasEnd) { break }
        }

        if (-not $hasHeader -or -not $hasEnd -or $idat.Length -eq 0 -or $stream.Position -ne $stream.Length) { throw 'Incomplete PNG data.' }
        $stride = [int]($width * 4)
        $rgba = [byte[]]::new([int]($stride * $height))
        $row = [byte[]]::new($stride + 1)
        $idat.Position = 0
        $zlib = [IO.Compression.ZLibStream]::new($idat, [IO.Compression.CompressionMode]::Decompress, $true)
        try {
            for ($y = 0; $y -lt $height; $y++) {
                $zlib.ReadExactly($row, 0, $row.Length)
                if ($row[0] -ne 0) { throw 'Unsupported PNG scanline filter.' }
                [Array]::Copy($row, 1, $rgba, ($y * $stride), $stride)
            }
            if ($zlib.ReadByte() -ne -1) { throw 'Unexpected extra PNG scanline data.' }
        }
        finally { $zlib.Dispose() }
        return [pscustomobject]@{
            Width  = [int]$width
            Height = [int]$height
            Rgba   = $rgba
        }
    }
    finally {
        $idat.Dispose()
        $reader.Dispose()
        $stream.Dispose()
    }
}
function Reject([byte[]]$bytes){$failed=$false;try{Read-OpenJadeMFT $bytes | Out-Null}catch{$failed=$true};Assert $failed 'Malformed input accepted.'}
# Independent fixture: a 4x4 atlas with empty glyph rectangles spanning one texel.
$b=New-Object byte[] (5248+16)
[Text.Encoding]::ASCII.GetBytes("Magma Font`0").CopyTo($b,0)
[BitConverter]::GetBytes([uint32]110).CopyTo($b,11)
[Text.Encoding]::ASCII.GetBytes('Fixture').CopyTo($b,15)
for($i=0;$i -lt 224;$i++){
    $o=84+23*$i;[BitConverter]::GetBytes([uint16](32+$i)).CopyTo($b,$o)
    [BitConverter]::GetBytes([single]0.125).CopyTo($b,$o+7)
    [BitConverter]::GetBytes([single]0.125).CopyTo($b,$o+11)
    [BitConverter]::GetBytes([single]0.375).CopyTo($b,$o+15)
    [BitConverter]::GetBytes([single]0.375).CopyTo($b,$o+19)
}
[BitConverter]::GetBytes([uint16]4).CopyTo($b,5244)
[BitConverter]::GetBytes([uint16]4).CopyTo($b,5246)
for($i=0;$i -lt 16;$i++){$b[5248+$i]=$i*17}
$font=Read-OpenJadeMFT $b
Assert ($font.Name -eq 'Fixture' -and $font.Glyphs.Count -eq 224) 'Fixture header mismatch.'
Assert ($font.Glyphs[223].Offset -eq 5213 -and $font.Glyphs[223].EndOffset -eq 5236) 'Offset mismatch.'
Assert ($font.Pixels[15] -eq 255 -and $font.Glyphs[0].Width -eq 0) 'Empty glyph or pixels mismatch.'
Reject ([byte[]]$b[0..5246])
Reject ([byte[]]$b[0..($b.Length-2)])
Reject ([byte[]]($b+0))
foreach($offset in @(0,11,84,86,5244)){$bad=$b.Clone();$bad[$offset]=0; if($offset -eq 86){$bad[$offset]=3};Reject $bad}
$bad=$b.Clone();[BitConverter]::GetBytes([single]::NaN).CopyTo($bad,91);Reject $bad
$bad=$b.Clone();[BitConverter]::GetBytes([single]1.5).CopyTo($bad,91);Reject $bad
$bad=$b.Clone();[BitConverter]::GetBytes([single]0.2).CopyTo($bad,91);Reject $bad
$bad=$b.Clone();for($i=15;$i -lt 79;$i++){$bad[$i]=65};Reject $bad
if($FontDirectory){
    $files=@(Get-ChildItem -LiteralPath $FontDirectory -Filter *.mft -File)
    Assert ($files.Count -eq 12) 'Expected the twelve-file reference corpus.'
    foreach($file in $files){
        $before=(Get-FileHash $file.FullName).Hash
        $raw=[IO.File]::ReadAllBytes($file.FullName);$f=Read-OpenJadeMFT $raw
        Assert ($f.Glyphs.Count -eq 224 -and $f.Pixels.Length -eq $raw.Length-5248) 'Real corpus mismatch.'
        Assert ((Get-FileHash $file.FullName).Hash -ceq $before) 'Input changed.'
    }
}
$report=Join-Path (Join-Path (Split-Path $PSScriptRoot -Parent) 'reports') ('openjade-mft-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($report)
$inputPath=Join-Path $report 'fixture.mft'
[IO.File]::WriteAllBytes($inputPath,$b)
$export=Join-Path $report 'export'
& (Join-Path $PSScriptRoot '../tools/Read-MFT.ps1') -Path $inputPath -OutputDirectory $export | Out-Null
Assert ((Get-FileHash $inputPath).Hash -ceq (Get-FileHash (Join-Path $export 'source.mft')).Hash) 'Source preservation failed.'
$image = Read-PngRgba (Join-Path $export 'atlas.png')
Assert ($image.Width -eq 4 -and $image.Height -eq 4) 'PNG dimensions mismatch.'
for ($i=0; $i -lt 16; $i++) {
    $offset = $i * 4
    Assert ($image.Rgba[$offset] -eq $i*17 -and $image.Rgba[$offset+1] -eq $image.Rgba[$offset] -and $image.Rgba[$offset+2] -eq $image.Rgba[$offset] -and $image.Rgba[$offset+3] -eq 255) 'PNG pixel mismatch.'
}
$failed=$false
try{& (Join-Path $PSScriptRoot '../tools/Read-MFT.ps1') -Path $inputPath -OutputDirectory $export | Out-Null}catch{$failed=$true}
Assert $failed 'Existing output directory was accepted.'
Write-Host "$script:checks MFT checks passed."