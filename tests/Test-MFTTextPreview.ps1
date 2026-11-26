#requires -Version 7.6
param([string]$FontDirectory)
Set-StrictMode -Version 3.0
$ErrorActionPreference='Stop'
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
$tool=Join-Path $PSScriptRoot '../tools/Export-MFTTextPreview.ps1'
$root=Join-Path (Join-Path (Split-Path $PSScriptRoot -Parent) 'reports') ('openjade-text-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($root)
# Independent 8x8 fixture, with a 2x2 glyph, negative bearing and explicit advance.
$b=New-Object byte[] 5312
[Text.Encoding]::ASCII.GetBytes("Magma Font`0").CopyTo($b,0)
[BitConverter]::GetBytes([uint32]110).CopyTo($b,11)
[Text.Encoding]::ASCII.GetBytes('Fixture').CopyTo($b,15)
for($i=0;$i -lt 224;$i++){
    $o=84+23*$i
    [BitConverter]::GetBytes([uint16](32+$i)).CopyTo($b,$o)
    foreach($delta in @(7,11)){[BitConverter]::GetBytes([single]0.0625).CopyTo($b,$o+$delta)}
    foreach($delta in @(15,19)){[BitConverter]::GetBytes([single]0.1875).CopyTo($b,$o+$delta)}
    $b[$o+6]=4
}
$o=84+23*(65-32);$b[$o+2]=2;$b[$o+3]=2;$b[$o+4]=255;$b[$o+5]=2;$b[$o+6]=3
foreach($delta in @(15,19)){[BitConverter]::GetBytes([single]0.4375).CopyTo($b,$o+$delta)}
[BitConverter]::GetBytes([uint16]8).CopyTo($b,5244)
[BitConverter]::GetBytes([uint16]8).CopyTo($b,5246)
$b[5257]=255;$b[5258]=128;$b[5265]=64;$b[5266]=0
$path=Join-Path $root 'fixture.mft';[IO.File]::WriteAllBytes($path,$b)
$out=Join-Path $root 'specimen'
$m=& $tool -Path $path -OutputDirectory $out -Text 'A A'
Assert ($m.Width -eq 43 -and $m.Height -eq 34 -and $m.Baseline -eq 18) 'Bounds mismatch.'
$positions=@(Import-Csv (Join-Path $out 'placements.csv'))
Assert ($positions[0].X -eq '-1' -and $positions[2].X -eq '6' -and $positions[2].PenX -eq '7') 'Bearing or space advance mismatch.'
$image = Read-PngRgba (Join-Path $out 'text.png')
Assert ($image.Rgba[(16*$image.Width+16)*4+3] -eq 255) 'Opaque coverage mismatch.'
Assert ($image.Rgba[(16*$image.Width+17)*4+3] -eq 128) 'Partial coverage mismatch.'
Assert ($image.Rgba[(17*$image.Width+16)*4+3] -eq 64) 'Crop origin mismatch.'
Assert ($image.Rgba[(17*$image.Width+17)*4+3] -eq 0 -and $image.Rgba[(16*$image.Width+20)*4+3] -eq 0) 'Transparency or space mismatch.'
Assert ($image.Rgba[(16*$image.Width+23)*4+3] -eq 255) 'Second glyph position mismatch.'
Assert ((Get-FileHash $path).Hash -ceq (Get-FileHash (Join-Path $out 'source.mft')).Hash) 'Source copy mismatch.'
$spaced=& $tool -Path $path -OutputDirectory (Join-Path $root 'spacing') -Text 'AA' -ExtraSpacing 2
Assert ($spaced.Width -eq 43) 'Extra spacing mismatch.'
$overlapPath=Join-Path $root 'overlap'
& $tool -Path $path -OutputDirectory $overlapPath -Text 'AA' -ExtraSpacing -3 | Out-Null
$image = Read-PngRgba (Join-Path $overlapPath 'text.png')
Assert ($image.Rgba[(16*$image.Width+17)*4+3] -eq 192 -and $image.Rgba[(17*$image.Width+16)*4+3] -eq 112) 'Source-over blending mismatch.'
$blank=& $tool -Path $path -OutputDirectory (Join-Path $root 'blank') -Text '  '
Assert ($blank.Width -eq 40 -and $blank.Height -eq 32) 'Space-only layout mismatch.'
foreach($case in @(@{Text='A';OutputDirectory=$out},@{Text="A`nB";OutputDirectory=(Join-Path $root 'bad')},@{Text=([string][char]233);OutputDirectory=(Join-Path $root 'extended')})){
    $failed=$false;try{& $tool -Path $path @case | Out-Null}catch{$failed=$true};Assert $failed 'Invalid request accepted.'
}
if($FontDirectory){
    $files=@(Get-ChildItem -LiteralPath $FontDirectory -Filter *.mft -File)
    Assert ($files.Count -eq 12) 'Expected twelve reference fonts.'
    foreach($file in $files){
        $hash=(Get-FileHash $file.FullName).Hash
        $result=& $tool -Path $file.FullName -OutputDirectory (Join-Path $root $file.BaseName) -Text 'Nouvelle partie'
        Assert ($result.Width -gt 32 -and $result.Height -gt 32 -and -not $result.GameRenderingValidated) 'Corpus rendering failed.'
        Assert ((Get-FileHash $file.FullName).Hash -ceq $hash) 'Real input changed.'
    }
}
Write-Host "$script:checks MFT text checks passed. Reports: $root"
