#requires -Version 5.1
<#
.SYNOPSIS
    Tests supported DDS decoding and optional real-data comparison with Pillow.
.PARAMETER TextureDirectory
    Optional extracted texture directory; all DDS files below it are checked.
.PARAMETER PythonPath
    Optional Python executable with Pillow for independent DDS and PNG checks.
#>
[CmdletBinding()]
param([string]$TextureDirectory,[string]$PythonPath)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Add-Type -Path (Join-Path $project 'src/OpenJade.Dds.cs') -ReferencedAssemblies System.Drawing
$run=Join-Path $project ('reports/dds-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks=New-Object 'System.Collections.Generic.List[string]'
$records=New-Object 'System.Collections.Generic.List[object]'
function Assert([bool]$Condition,[string]$Name){if(-not $Condition){throw "FAIL: $Name"};$checks.Add($Name)}
function Refuses([scriptblock]$Action,[string]$Name){$failed=$false;try{& $Action | Out-Null}catch{$failed=$true};Assert $failed $Name}
function Put([byte[]]$Bytes,[int]$Offset,[uint32]$Value){[BitConverter]::GetBytes($Value).CopyTo($Bytes,$Offset)}
function Hash([byte[]]$Bytes){$sha=[Security.Cryptography.SHA256]::Create();try{[BitConverter]::ToString($sha.ComputeHash($Bytes)).Replace('-','')}finally{$sha.Dispose()}}
function Fixture([bool]$Bc3=$false,[int]$Width=4,[int]$Height=4){
    $size=if($Bc3){16}else{8};$b=New-Object byte[] (128+[int][Math]::Ceiling($Width/4.0)*[int][Math]::Ceiling($Height/4.0)*$size)
    Put $b 0 542327876;Put $b 4 124;Put $b 8 528391;Put $b 12 $Height;Put $b 16 $Width
    Put $b 20 ($b.Length-128);Put $b 76 32;Put $b 80 4
    Put $b 84 $(if($Bc3){894720068}else{827611204});Put $b 108 4096
    return ,$b
}
function Pixel($Image,[int]$Index){[BitConverter]::ToString($Image.Rgba,$Index*4,4)}
function Record([byte[]]$Bytes,[string]$Name){
    $path=Join-Path $run ($Name+'.dds');[IO.File]::WriteAllBytes($path,$Bytes)
    $image=[OpenJade.Dds]::Decode($Bytes);$png=Join-Path $run ($Name+'.png')
    [OpenJade.Dds]::SavePng($image,$png,$false)
    $records.Add([pscustomobject]@{SourcePath=$path;PngPath=$png;RgbaSHA256=(Hash $image.Rgba)})
}
$b=Fixture;$b[128]=0;$b[129]=248;$b[130]=224;$b[131]=7
Put $b 132 3840206052
$image=[OpenJade.Dds]::Decode($b)
Assert ((Pixel $image 0) -eq 'FF-00-00-FF') 'BC1 red endpoint'
Assert ((Pixel $image 1) -eq '00-FF-00-FF') 'BC1 green endpoint'
Assert ((Pixel $image 2) -eq 'AA-55-00-FF' -and (Pixel $image 3) -eq '55-AA-00-FF') 'BC1 four-color interpolation and index order'
Record $b 'bc1-four'
$b=Fixture;$b[130]=255;$b[131]=255;Put $b 132 3840206052
$image=[OpenJade.Dds]::Decode($b)
Assert ((Pixel $image 2) -eq '7F-7F-7F-FF' -and (Pixel $image 3) -eq '00-00-00-00') 'BC1 three-color mode and transparency'
Record $b 'bc1-alpha'
foreach($mode in @(0,1)){
    $b=Fixture $true
    $b[128]=if($mode -eq 0){255}else{0};$b[129]=if($mode -eq 0){0}else{255}
    $bits=[uint64]0;for($i=0;$i -lt 16;$i++){$bits=$bits -bor ([uint64]($i%8) -shl (3*$i))}
    for($i=0;$i -lt 6;$i++){$b[130+$i]=[byte](($bits -shr (8*$i)) -band 255)}
    $b[138]=255;$b[139]=255;Put $b 140 ([uint32]::MaxValue)
    $image=[OpenJade.Dds]::Decode($b)
    $expected=if($mode -eq 0){@(255,0,218,182,145,109,72,36)}else{@(0,255,51,102,153,204,0,255)}
    $actual=@(for($i=0;$i -lt 8;$i++){$image.Rgba[4*$i+3]})
    Assert (($actual -join ',') -eq ($expected -join ',')) "BC3 alpha palette mode $mode"
    Assert ($image.Rgba[0] -eq 170) 'BC3 always uses four colors with reversed endpoints'
    Record $b "bc3-$mode"
}
$b=Fixture $false 5 3;$b[129]=248;$b[138]=224;$b[139]=7;Put $b 140 1431655765
$image=[OpenJade.Dds]::Decode($b)
Assert ($image.Rgba.Length -eq 60 -and (Pixel $image 4) -eq '00-FF-00-FF' -and (Pixel $image 5) -eq 'FF-00-00-FF') 'Block placement and partial edge cropping'
Record $b 'bc1-edge'
$valid=Fixture
foreach($change in @(@{O=0;V=0},@{O=4;V=123},@{O=76;V=31},@{O=12;V=0},@{O=16;V=8193},@{O=24;V=1},@{O=28;V=2},@{O=80;V=0},@{O=84;V=0},@{O=112;V=512})){
    $bad=[byte[]]$valid.Clone();Put $bad $change.O $change.V
    Refuses {[OpenJade.Dds]::Decode($bad)} "Invalid or unsupported header field $($change.O)"
}
Refuses {[OpenJade.Dds]::Decode([byte[]]$valid[0..126])} 'Truncated header refused'
Refuses {[OpenJade.Dds]::Decode([byte[]]$valid[0..134])} 'Truncated block refused'
Refuses {[OpenJade.Dds]::Decode([byte[]]($valid+@(0)))} 'Extra payload bytes refused'
$oversized=[byte[]]$valid.Clone();Put $oversized 12 8192;Put $oversized 16 8192
Refuses {[OpenJade.Dds]::Decode($oversized)} 'Combined pixel allocation limit enforced'
$fixture=Join-Path $run 'bc3-0.dds';$before=(Get-FileHash $fixture).Hash
$out=Join-Path $run 'tool'
$manifest=& (Join-Path $project 'tools/Export-DDSPreview.ps1') $fixture $out
Assert ($manifest.SourceSHA256 -ceq $before -and (Get-FileHash $fixture).Hash -ceq $before) 'Input unchanged'
Assert ((Get-FileHash (Join-Path $out 'source.dds')).Hash -ceq $before) 'Stored DDS preserved'
Assert ((Get-Content (Join-Path $out 'texture.json') -Raw | ConvertFrom-Json).Width -eq 4) 'Manifest exported'
$png=[Drawing.Bitmap]::FromFile((Join-Path $out 'texture.png'))
$preview=[Drawing.Bitmap]::FromFile((Join-Path $out 'preview.png'))
try{Assert ($png.GetPixel(1,0).A -eq 0 -and $preview.GetPixel(1,0).A -eq 255 -and $preview.GetPixel(1,0).R -eq 48) 'PNG alpha preserved and preview background separate'}finally{$png.Dispose();$preview.Dispose()}
Refuses {& (Join-Path $project 'tools/Export-DDSPreview.ps1') $fixture $out} 'Existing output refused'
Refuses {& (Join-Path $project 'tools/Export-DDSPreview.ps1') $fixture (Join-Path $project 'game/forbidden')} 'Game output refused'
$badFile=Join-Path $run 'invalid.dds';[IO.File]::WriteAllBytes($badFile,[byte[]]$valid[0..126])
$badOutput=Join-Path $run 'invalid-output'
Refuses {& (Join-Path $project 'tools/Export-DDSPreview.ps1') $badFile $badOutput} 'Invalid file refused by export command'
Assert (-not(Test-Path $badOutput)) 'Invalid file creates no output directory'
$realCount=0
if($TextureDirectory){
    foreach($file in @(Get-ChildItem -LiteralPath $TextureDirectory -Filter *.dds -File -Recurse)){
        $before=(Get-FileHash $file.FullName).Hash
        $bytes=[IO.File]::ReadAllBytes($file.FullName);$image=[OpenJade.Dds]::Decode($bytes)
        $png=Join-Path $run ("real-$realCount.png");[OpenJade.Dds]::SavePng($image,$png,$false)
        Assert ((Get-FileHash $file.FullName).Hash -ceq $before) "Real input unchanged: $($file.Name)"
        $records.Add([pscustomobject]@{SourcePath=$file.FullName;PngPath=$png;RgbaSHA256=(Hash $image.Rgba)})
        $realCount++
    }
    Assert ($realCount -gt 0) 'Real DDS inventory is nonempty'
}
$comparison=Join-Path $run 'comparison-input.json'
ConvertTo-Json -InputObject @($records.ToArray()) -Depth 3 | Set-Content $comparison -Encoding UTF8
if($PythonPath){
    & $PythonPath (Join-Path $PSScriptRoot 'Compare-DDSReference.py') $comparison (Join-Path $run 'pillow-verification.json')
    if($LASTEXITCODE -ne 0){throw 'Independent DDS comparison failed.'}
    Assert $true 'Independent DDS decoder and PNG round-trip agree byte for byte'
}
[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray();RealTextures=$realCount;ReferenceCompared=[bool]$PythonPath} | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks; $realCount real textures. Results: $run"
