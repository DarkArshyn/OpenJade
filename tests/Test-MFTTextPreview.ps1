#requires -Version 5.1
param([string]$FontDirectory)
$ErrorActionPreference='Stop'
$script:checks=0
function Assert($condition,$message){if(-not $condition){throw $message};$script:checks++}
$tool=Join-Path $PSScriptRoot '../tools/Export-MFTTextPreview.ps1'
$root=Join-Path ([IO.Path]::GetTempPath()) ('openjade-text-'+[guid]::NewGuid().ToString('N'))
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
$image=[Drawing.Bitmap]::FromFile((Join-Path $out 'text.png'))
try{
    Assert ($image.GetPixel(16,16).A -eq 255) 'Opaque coverage mismatch.'
    Assert ($image.GetPixel(17,16).A -eq 128) 'Partial coverage mismatch.'
    Assert ($image.GetPixel(16,17).A -eq 64) 'Crop origin mismatch.'
    Assert ($image.GetPixel(17,17).A -eq 0 -and $image.GetPixel(20,16).A -eq 0) 'Transparency or space mismatch.'
    Assert ($image.GetPixel(23,16).A -eq 255) 'Second glyph position mismatch.'
}finally{$image.Dispose()}
Assert ((Get-FileHash $path).Hash -ceq (Get-FileHash (Join-Path $out 'source.mft')).Hash) 'Source copy mismatch.'
$spaced=& $tool -Path $path -OutputDirectory (Join-Path $root 'spacing') -Text 'AA' -ExtraSpacing 2
Assert ($spaced.Width -eq 43) 'Extra spacing mismatch.'
$overlapPath=Join-Path $root 'overlap'
& $tool -Path $path -OutputDirectory $overlapPath -Text 'AA' -ExtraSpacing -3 | Out-Null
$image=[Drawing.Bitmap]::FromFile((Join-Path $overlapPath 'text.png'))
try{Assert ($image.GetPixel(17,16).A -eq 192 -and $image.GetPixel(16,17).A -eq 112) 'Source-over blending mismatch.'}finally{$image.Dispose()}
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
