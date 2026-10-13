#requires -Version 5.1
param([string]$FontDirectory)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot '../src/OpenJade.MFT.psm1') -Force
$script:checks=0
function Assert($condition,$message){if(-not $condition){throw $message};$script:checks++}
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
$report=Join-Path ([IO.Path]::GetTempPath()) ('openjade-mft-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($report)
$inputPath=Join-Path $report 'fixture.mft'
[IO.File]::WriteAllBytes($inputPath,$b)
$export=Join-Path $report 'export'
& (Join-Path $PSScriptRoot '../tools/Read-MFT.ps1') -Path $inputPath -OutputDirectory $export | Out-Null
Assert ((Get-FileHash $inputPath).Hash -ceq (Get-FileHash (Join-Path $export 'source.mft')).Hash) 'Source preservation failed.'
$image=[Drawing.Bitmap]::FromFile((Join-Path $export 'atlas.png'))
try{
    Assert ($image.Width -eq 4 -and $image.Height -eq 4) 'PNG dimensions mismatch.'
    for($i=0;$i -lt 16;$i++){
        $pixel=$image.GetPixel(($i%4),[int][Math]::Floor($i/4))
        Assert ($pixel.R -eq $i*17 -and $pixel.G -eq $pixel.R -and $pixel.B -eq $pixel.R -and $pixel.A -eq 255) 'PNG pixel mismatch.'
    }
}finally{$image.Dispose()}
$failed=$false
try{& (Join-Path $PSScriptRoot '../tools/Read-MFT.ps1') -Path $inputPath -OutputDirectory $export | Out-Null}catch{$failed=$true}
Assert $failed 'Existing output directory was accepted.'
Write-Host "$script:checks MFT checks passed."
