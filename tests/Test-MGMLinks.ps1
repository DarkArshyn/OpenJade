#requires -Version 5.1
<#
.SYNOPSIS
    Tests local MGM name resolution, resource candidates and reports.
.PARAMETER MenuDirectory
    Optional extracted menu directory containing MGM, texture and fonts files.
.EXAMPLE
    .\tests\Test-MGMLinks.ps1
#>
[CmdletBinding()]
param([string]$MenuDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.MGMLinks.psm1')
$run=Join-Path $project ('reports/mgm-links-'+[guid]::NewGuid().ToString('N'))
$assets=Join-Path $run 'assets'
[void][IO.Directory]::CreateDirectory((Join-Path $assets 'texture'))
[void][IO.Directory]::CreateDirectory((Join-Path $assets 'fonts'))
# Synthetic placeholders test path matching only; no decoder is being tested.
[IO.File]::WriteAllBytes((Join-Path $assets 'texture/a.dds'),[byte[]](1,2,3))
[IO.File]::WriteAllBytes((Join-Path $assets 'fonts/demo.mft'),[byte[]](4,5,6))
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name) { if (-not $Condition) {throw "FAIL: $Name"}; $checks.Add($Name) }
function Assert-Throws([scriptblock]$Action,[string]$Name) {
    $failed=$false
    try { & $Action | Out-Null } catch { $failed=$true }
    Assert $failed $Name
}
function Analyze([string]$Text) {
    $path=Join-Path $run ([guid]::NewGuid().ToString('N')+'.mgm')
    [IO.File]::WriteAllText($path,$Text,[Text.Encoding]::ASCII)
    Get-OpenJadeMGMLinks -Path $path -AssetRoot $assets
}
$material='<MATERIAL><NAME>Glow</NAME><STAGE><FILE>\Texture\A.dds</FILE></STAGE></MATERIAL>'
$font='<FONTS><Pixmap><NAME>Demo</NAME></Pixmap></FONTS>'
$image='<IMAGE><NAME>Logo</NAME><MATERIAL>Glow</MATERIAL></IMAGE>'
$text='<TEXT><NAME>Title</NAME><FONT>Demo</FONT></TEXT>'
$a=Analyze ('<PACKAGE><MATERIALS>'+$material+'</MATERIALS>'+$font+$image+$text+'</PACKAGE>')
Assert ($a.Summary.ResolvedNames -eq 2 -and $a.Summary.AttentionCount -eq 0) 'Unique names resolve locally'
$imageLink=@($a.Links | Where-Object Kind -eq MaterialReference)[0]
Assert ($imageLink.OwnerName -eq 'Logo' -and $imageLink.TargetOffset -eq $a.Document.Materials[0].Offset) 'Image links to precise definition offset'
$texture=@($a.Links | Where-Object Kind -eq TextureFile)[0]
Assert ($texture.Status -eq 'CaseInsensitiveFileMatch' -and (Test-Path -LiteralPath $texture.TargetPath)) 'Leading separator and case differences recorded'
$fontFile=@($a.Links | Where-Object Kind -eq FontFile)[0]
Assert ($fontFile.Status -eq 'FontFileCandidate') 'Font filename remains candidate'
Assert ($a.Elements.Count -eq 2 -and $a.Elements[0].ResourceStatus -eq 'CaseInsensitiveFileMatch' -and $a.Elements[1].ResourceStatus -eq 'FontFileCandidate') 'Element chains preserve resource evidence'
Assert ($imageLink.SourceOffset -eq $a.Document.Nodes[$imageLink.SourceNodeIndex].Offset) 'Source offsets are traceable'
$missing=Analyze '<ROOT><IMAGE><MATERIAL>Absent</MATERIAL></IMAGE><TEXT><FONT>Absent</FONT></TEXT></ROOT>'
Assert (@($missing.Links | Where-Object Status -eq MissingDefinition).Count -eq 2) 'Missing names reported'
Assert (@($missing.Elements | Where-Object ResourceStatus -eq UnresolvedReference).Count -eq 2) 'Unresolved element chains retained'
$duplicate=Analyze ('<ROOT>'+$material+$material+$image+'</ROOT>')
Assert (@($duplicate.Links | Where-Object Status -eq AmbiguousDefinition).Count -eq 1) 'Duplicate definitions are ambiguous'
Assert (@($duplicate.Links | Where-Object Kind -eq MaterialReference)[0].TargetNodeIndex -eq -1) 'Ambiguity chooses no target'
$case=Analyze ('<ROOT>'+$material+'<IMAGE><MATERIAL>glow</MATERIAL></IMAGE></ROOT>')
Assert (@($case.Links | Where-Object Status -eq CaseMismatchCandidate).Count -eq 1) 'Case-only names are candidates'
$missingFile=Analyze ('<ROOT>'+$material.Replace('A.dds','missing.dds')+$font.Replace('Demo','Absent')+'</ROOT>')
Assert (@($missingFile.Links | Where-Object Status -eq MissingFile).Count -eq 2) 'Missing texture and font files reported'
foreach ($unsafe in @('../escape.dds','C:\escape.dds','\\host\share\a.dds','texture/NUL.dds','texture/a.dds:stream')) {
    $bad=Analyze ('<ROOT>'+$material.Replace('\Texture\A.dds',$unsafe)+'</ROOT>')
    Assert (@($bad.Links | Where-Object Status -eq UnsafePath).Count -eq 1) "Unsafe resource rejected: $unsafe"
}
$noStage=Analyze ('<ROOT><MATERIAL><NAME>Glow</NAME></MATERIAL>'+$image+'</ROOT>')
Assert ($noStage.Elements[0].ReferenceStatus -eq 'ResolvedName' -and $noStage.Elements[0].ResourceStatus -eq 'NoFileDeclaration' -and $noStage.Summary.AttentionCount -eq 1) 'Definition without file stays explicit'
$broken=Analyze ('<ROOT>'+$material+$image)
Assert ($broken.Summary.StructuralDiagnostics -gt 0 -and @($broken.Links | Where-Object Status -ne UncertainStructure).Count -eq 0) 'Malformed document resolution withheld'
$foreign=Analyze $image
Assert ($foreign.Links[0].Status -eq 'MissingDefinition') 'Other documents are not searched'
$multi=Analyze ('<ROOT>'+$material.Replace('</STAGE>','</STAGE><STAGE><FILE>texture/a.dds</FILE></STAGE>')+$image+'</ROOT>')
Assert ($multi.Elements.Count -eq 2) 'Multiple stages retain multiple edges'
$ambiguousFont=Analyze ('<ROOT>'+$font+$font+$text+'</ROOT>')
Assert (@($ambiguousFont.Links | Where-Object Status -eq AmbiguousDefinition).Count -eq 1) 'Duplicate font declarations are ambiguous'
$noName=Analyze '<ROOT><IMAGE><MATERIAL>Absent</MATERIAL></IMAGE><FONTS><Pixmap><NAME>../escape</NAME></Pixmap></FONTS></ROOT>'
Assert (@($noName.Links | Where-Object Status -eq UnsafePath).Count -eq 1) 'Font path separators rejected'
$module=Get-Module OpenJade.MGMLinks
$collision=& $module { Get-MGMFileMatch -Value 'Texture/a.dds' -Files @([pscustomobject]@{RelativePath='texture/a.dds'},[pscustomobject]@{RelativePath='Texture/A.dds'}) }
Assert ($collision.Status -eq 'AmbiguousFile' -and $collision.Candidates.Count -eq 2) 'Case-colliding file inventory does not choose arbitrarily'
$output=Join-Path $run 'report'
Export-OpenJadeMGMLinks -Analysis $a -OutputDirectory $output | Out-Null
$rows=@(Import-Csv (Join-Path $output 'elements.csv'))
Assert ($rows.Count -eq 2 -and $rows[0].ElementName -eq 'Logo') 'Element CSV round trip'
Assert ([IO.File]::ReadAllText((Join-Path $output 'references.txt')).Contains('FontFileCandidate')) 'Readable report labels candidates'
Assert-Throws { Export-OpenJadeMGMLinks -Analysis $a -OutputDirectory $output } 'Existing output refused'
Assert-Throws { Export-OpenJadeMGMLinks -Analysis $a -OutputDirectory (Join-Path $project 'game/forbidden') } 'Game report output refused'
$empty=Analyze ''
$emptyOutput=Join-Path $run 'empty'
Export-OpenJadeMGMLinks -Analysis $empty -OutputDirectory $emptyOutput | Out-Null
Assert ($empty.Links.Count -eq 0 -and [IO.File]::ReadAllText((Join-Path $emptyOutput 'links.csv')).StartsWith('"LinkId"')) 'Empty document has valid empty report'
$command=& (Join-Path $project 'tools/Resolve-MGMResources.ps1') -Path $a.Document.Path -AssetRoot $assets -OutputDirectory (Join-Path $run 'command')
Assert ($command.Summary.ResolvedNames -eq 2) 'User command works'
$realResults=@()
if ($MenuDirectory) {
    $files=@(Get-ChildItem -LiteralPath $MenuDirectory -Filter *.mgm -File)
    Assert ($files.Count -gt 0) 'Real set is non-empty'
    $hashes=@{}
    foreach ($file in Get-ChildItem -LiteralPath $MenuDirectory -Recurse -File) { $hashes[$file.FullName]=(Get-FileHash -LiteralPath $file.FullName).Hash }
    foreach ($file in $files) {
        $real=Get-OpenJadeMGMLinks -Path $file.FullName -AssetRoot $MenuDirectory
        Assert ($real.Summary.StructuralDiagnostics -eq 0) "Real structure is clean: $($file.Name)"
        Assert ($real.Summary.AttentionCount -eq 0) "Real references have matches: $($file.Name)"
        Assert (@($real.Links | Where-Object { $_.Kind -eq 'TextureFile' -and $_.Status -notin @('FileFound','CaseInsensitiveFileMatch') }).Count -eq 0) "Real textures exist: $($file.Name)"
        Assert (@($real.Links | Where-Object { $_.Kind -eq 'FontFile' -and $_.Status -ne 'FontFileCandidate' }).Count -eq 0) "Real font candidates exist: $($file.Name)"
        Export-OpenJadeMGMLinks -Analysis $real -OutputDirectory (Join-Path $run $file.BaseName) | Out-Null
        $realResults+=$real.Summary
    }
    $unchanged=$true
    foreach ($path in $hashes.Keys) { if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$path]) {$unchanged=$false} }
    Assert $unchanged 'All input MGM, textures and font files remain unchanged'
}
[pscustomobject]@{Date=(Get-Date).ToString('o');PowerShell=$PSVersionTable.PSVersion.ToString();Checks=$checks.Count;Passed=$checks.ToArray();RealFiles=$realResults} |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
$realResults | Format-Table FileName,MaterialReferences,FontReferences,TextureDeclarations,FontDeclarations,ResolvedNames,AttentionCount
