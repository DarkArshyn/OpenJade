#requires -Version 5.1
<#
.SYNOPSIS
    Tests MGM structure, raw-byte preservation, material types and reports.
.PARAMETER MgmDirectory
    Optional directory containing local MGM files. Original files are only read.
.EXAMPLE
    .\tests\Test-MGM.ps1
#>
[CmdletBinding()]
param([string]$MgmDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$project=Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.MGM.psm1')
$run=Join-Path $project ('reports/mgm-'+[guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$encoding=[Text.Encoding]::GetEncoding(28591)
$checks=New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $checks.Add($Name)
}
function Assert-Throws([scriptblock]$Action,[string]$Name) {
    $failed=$false
    try { & $Action | Out-Null } catch { $failed=$true }
    Assert $failed $Name
}
function Read-Fixture([string]$Text) {
    $path=Join-Path $run ([guid]::NewGuid().ToString('N')+'.mgm')
    [IO.File]::WriteAllBytes($path,$encoding.GetBytes($Text))
    Get-OpenJadeMGM -Path $path
}
$reference="<MATERIAL>  Glow`r`n</MATERIAL>"
$definition='<MATERIAL><NAME>Glow</NAME><STAGE><FILE>a.dds</FILE><REGION>r</REGION><BLENDOP>add</BLENDOP></STAGE></MATERIAL>'
$text='xx<ROOT><IMAGE>'+$reference+'</IMAGE><MATERIALS>'+$definition+'</MATERIALS></ROOT>zz'
$d=Read-Fixture $text
Assert ($d.Summary.DiagnosticCount -eq 0) 'Balanced structure has no diagnostics'
Assert ($d.Summary.DefinitionCount -eq 1 -and $d.Summary.ReferenceCount -eq 1) 'Material counts'
$r=$d.Materials[0]; $m=$d.Materials[1]
Assert ($r.GetType().Name -eq 'MaterialReference') 'Reference concrete type'
Assert ($m.GetType().Name -eq 'MaterialDefinition') 'Definition concrete type'
Assert ($r.PSObject.Properties.Name -notcontains 'StageCount') 'Reference has no stage fields'
Assert ($r.Parent -eq 'IMAGE' -and $r.Name -eq 'Glow') 'Reference under IMAGE'
Assert ($r.RawText -ceq $reference) 'Raw reference whitespace'
Assert ($r.Offset -eq $text.IndexOf($reference) -and $r.EndOffset -eq $r.Offset+$reference.Length) 'Reference byte offsets'
Assert ($m.StageCount -eq 1 -and $m.Files -eq 'a.dds' -and $m.Regions -eq 'r' -and $m.BlendOps -eq 'add') 'Definition stage data'
Assert ($m.RawText -ceq $definition) 'Definition source text'
Assert ($d.Bytes.Length -eq $text.Length -and $encoding.GetString($d.Bytes) -ceq $text) 'Whole file including prefix and suffix preserved'
foreach ($node in $d.Nodes) {
    Assert ($node.RawText -ceq $text.Substring($node.Offset,$node.Length)) 'Node source slice'
}
$nested=Read-Fixture '<MATERIAL><NAME>Outer</NAME><MATERIAL><NAME>Inner</NAME><STAGE><FILE>inner.dds</FILE></STAGE></MATERIAL></MATERIAL>'
Assert ($nested.Materials[0].StageCount -eq 0 -and $nested.Materials[1].Files -eq 'inner.dds') 'Nested materials do not steal children'
$sibling=Read-Fixture '<MATERIAL><STAGE><FILE>a.dds</FILE></STAGE></MATERIAL><MATERIAL><STAGE><FILE>b.dds</FILE></STAGE></MATERIAL>'
Assert ($sibling.Materials[0].Files -eq 'a.dds' -and $sibling.Materials[1].Files -eq 'b.dds') 'Sibling stage ownership'
$unknown=Read-Fixture '<ROOT><MATERIAL></MATERIAL><MATERIAL><OTHER>x</OTHER></MATERIAL></ROOT>'
Assert ($unknown.Summary.UnclassifiedCount -eq 2) 'Empty and unknown material containers are unclassified'
$unclosed=Read-Fixture '<MATERIAL><NAME>Open</NAME>'
Assert ($unclosed.Materials[0].Length -eq 0 -and -not $unclosed.Materials[0].Closed) 'Unclosed range convention'
Assert ($unclosed.Materials[0].RawText -eq '<MATERIAL>' -and $unclosed.Materials[0].RawTextEndOffset -eq 10) 'Unclosed raw limited to observed opening tag'
Assert ($unclosed.Diagnostics[0].Code -eq 'UnclosedNode') 'Unclosed diagnostic'
$broken=Read-Fixture '<A><B></A>'
Assert (@($broken.Diagnostics | Where-Object Code -eq MismatchedClosing).Count -eq 1) 'Mismatch diagnostic'
Assert (@($broken.Diagnostics | Where-Object Code -eq UnclosedNode).Count -eq 2) 'Mismatch does not repair stack'
Assert ($broken.Nodes[0].Length -eq 0 -and $broken.Nodes[1].Length -eq 0) 'Mismatch invents no end offsets'
$orphan=Read-Fixture '</X><A>ok</A>'
Assert ($orphan.Diagnostics[0].Code -eq 'UnmatchedClosing' -and $orphan.Nodes[0].Value -eq 'ok') 'Orphan closing retains later structure'
$case=Read-Fixture '<A>x</a>'
Assert (-not $case.Nodes[0].Closed) 'Tag names are case-sensitive'
$unsupported=Read-Fixture '<A x="1"/><B/>'
Assert ($unsupported.Summary.NodeCount -eq 1 -and $unsupported.Diagnostics.Count -eq 1) 'Attributes are reported and bare self-closing tags are read'
$selfClosing=Read-Fixture '<ROOT><X/><MATERIAL/><MATERIAL>ref</MATERIAL></ROOT>'
Assert ($selfClosing.Summary.SelfClosingCount -eq 2 -and $selfClosing.Diagnostics.Count -eq 0) 'Self-closing nodes preserve stack balance'
Assert ($selfClosing.Materials[0].Length -eq 11 -and $selfClosing.Materials[0].RawText -eq '<MATERIAL/>' -and $selfClosing.Materials[0].Closed) 'Self-closing material source range'
Assert ($selfClosing.Materials[1].Parent -eq 'ROOT' -and $selfClosing.Materials[1].Type -eq 'MATERIAL_REFERENCE') 'Self-closing nodes do not capture following siblings'
$bytes=Read-Fixture ('<MATERIAL>A'+[char]233+[char]0+'</MATERIAL>')
Assert ([Convert]::ToBase64String($encoding.GetBytes($bytes.Materials[0].RawText)) -eq [Convert]::ToBase64String($bytes.Bytes)) 'Latin-1 raw mapping is byte-reversible'
$output=Join-Path $run 'report'
$before=(Get-FileHash -LiteralPath $d.Path).Hash
Export-OpenJadeMGMReport -Document $d -OutputDirectory $output | Out-Null
$csv=@(Import-Csv -LiteralPath (Join-Path $output 'materials.csv'))
Assert ($csv.Count -eq 2 -and $csv[0].StageCount -eq '' -and $csv[1].Files -eq 'a.dds') 'Reference-first CSV preserves definition columns'
Assert ($csv[0].RawText -ceq $r.RawText) 'CSV multiline raw round trip'
$tree=[IO.File]::ReadAllText((Join-Path $output 'structure.txt'))
Assert ($tree.Contains('MATERIAL_REFERENCE') -and $tree.Contains('MATERIAL_DEFINITION')) 'Readable material types'
Assert ((Get-FileHash -LiteralPath $d.Path).Hash -eq $before) 'Report leaves source unchanged'
Assert-Throws { Export-OpenJadeMGMReport -Document $d -OutputDirectory $output } 'Existing report refused'
Assert-Throws { Export-OpenJadeMGMReport -Document $d -OutputDirectory (Join-Path $project 'game/forbidden') } 'Protected game report refused'
foreach ($emptyText in @('', 'binary'+[char]0+[char]255, '<ROOT></ROOT>')) {
    $empty=Read-Fixture $emptyText
    Assert ($empty.Materials.Count -eq 0) 'No materials supported'
    $emptyOutput=Join-Path $run ([guid]::NewGuid().ToString('N'))
    Export-OpenJadeMGMReport -Document $empty -OutputDirectory $emptyOutput | Out-Null
    Assert ([IO.File]::ReadAllText((Join-Path $emptyOutput 'materials.csv')).StartsWith('"Index"')) 'Empty material table has header'
}
$fromCommand=& (Join-Path $project 'tools/Read-MGM.ps1') -Path $d.Path -OutputDirectory (Join-Path $run 'command')
Assert ($fromCommand.Summary.SHA256 -eq $d.Summary.SHA256) 'User command returns parsed document'
$realResults=@()
if ($MgmDirectory) {
    $files=@(Get-ChildItem -LiteralPath $MgmDirectory -Filter '*.mgm' -File)
    Assert ($files.Count -gt 0) 'Real MGM set is non-empty'
    $known=@{
        '779AC0ECF54814AF05A536BB90E8015AE3360F168613F41C40D64A7B5D3FA240'=@(17,33)
        '06E6142A750982308AA92400FCC0C84F1153D298CD21E7EB90B74575D140DBA0'=@(1,3)
        'B7D4CD1B56FF4C14CC40E38CEF16D8A263E796822FD28BF9DF4C99EC7838118D'=@(3,5)
    }
    foreach ($file in $files) {
        $before=(Get-FileHash -LiteralPath $file.FullName).Hash
        $real=Get-OpenJadeMGM -Path $file.FullName
        $sourceText=$encoding.GetString($real.Bytes)
        $valid=$true
        foreach ($node in $real.Nodes) {
            if ($node.RawText -cne $sourceText.Substring($node.Offset,$node.RawTextEndOffset-$node.Offset)) { $valid=$false }
            if ($node.Closed -and $node.EndOffset -ne ($node.Offset+$node.Length)) { $valid=$false }
            if ($node.ParentIndex -ge $node.Index) { $valid=$false }
        }
        Assert $valid "Real node ranges and raw slices: $($file.Name)"
        $valid=$true
        foreach ($material in $real.Materials) {
            if ($material.RawText -cne $sourceText.Substring($material.Offset,$material.RawTextEndOffset-$material.Offset)) { $valid=$false }
        }
        Assert $valid "Real material raw slices: $($file.Name)"
        if ($known.ContainsKey($before)) {
            Assert ($real.Summary.DefinitionCount -eq $known[$before][0] -and $real.Summary.ReferenceCount -eq $known[$before][1]) "Known material counts: $($file.Name)"
            Assert ($real.Diagnostics.Count -eq 0) "Known balanced structure: $($file.Name)"
        }
        $realOutput=Join-Path $run $file.BaseName
        Export-OpenJadeMGMReport -Document $real -OutputDirectory $realOutput | Out-Null
        Assert (@(Import-Csv (Join-Path $realOutput 'materials.csv')).Count -eq $real.Materials.Count) "Real report material count: $($file.Name)"
        Assert ((Get-FileHash -LiteralPath $file.FullName).Hash -eq $before) "Real source unchanged: $($file.Name)"
        $realResults+=$real.Summary
    }
}
[pscustomobject]@{ Date=(Get-Date).ToString('o'); PowerShell=$PSVersionTable.PSVersion.ToString()
    Checks=$checks.Count; Passed=$checks.ToArray(); RealFiles=$realResults } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
$realResults | Format-Table FileName,TagCount,NodeCount,DefinitionCount,ReferenceCount,DiagnosticCount
