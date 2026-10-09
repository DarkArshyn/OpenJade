#requires -Version 5.1
Set-StrictMode -Version Latest

class MaterialRecord {
    [int]$Index
    [int]$NodeIndex
    [int]$Offset
    [string]$HexOffset
    [string]$Type
    [string]$Name
    [int]$Length
    [int]$EndOffset
    [string]$RawText
    [int]$RawTextEndOffset
    [string]$Parent
    [int]$ParentIndex
    [bool]$Closed
}
class MaterialDefinition : MaterialRecord {
    [int]$StageCount
    [string]$Files
    [string]$Regions
    [string]$BlendOps
}
class MaterialReference : MaterialRecord {}
class MaterialUnclassified : MaterialRecord {}

function Get-OpenJadeMGMMaterials {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [array]$Nodes,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [byte[]]$Bytes
    )
    $materials = New-Object System.Collections.ArrayList
    # Latin-1 is a reversible byte-to-character mapping, not an assertion about
    # the MGM text encoding. Unlike ASCII it preserves bytes above 0x7F.
    $rawEncoding = [System.Text.Encoding]::GetEncoding(28591)
    $childrenByParent = @{}
    foreach ($node in $Nodes) {
        if (-not $childrenByParent.ContainsKey($node.ParentIndex)) {
            $childrenByParent[$node.ParentIndex] = New-Object System.Collections.ArrayList
        }
        [void]$childrenByParent[$node.ParentIndex].Add($node)
    }
    foreach ($node in $Nodes) {
        if ($node.Name -cne 'MATERIAL') { continue }
        $children = @($childrenByParent[$node.Index] | Where-Object { $null -ne $_ })
        $names = @($children | Where-Object { $_.Name -ceq 'NAME' })
        $stages = @($children | Where-Object { $_.Name -ceq 'STAGE' })
        if ($names.Count -gt 0 -or $stages.Count -gt 0) {
            $material = [MaterialDefinition]::new()
            $material.Type = 'MATERIAL_DEFINITION'
            if ($names.Count -gt 0) { $material.Name = $names[0].Value }
            $material.StageCount = $stages.Count
            $files = @(); $regions = @(); $blendOps = @()
            foreach ($stage in $stages) {
                foreach ($child in @($childrenByParent[$stage.Index])) {
                    if ($null -eq $child -or $child.Value -eq '') { continue }
                    switch -CaseSensitive ($child.Name) {
                        'FILE' { $files += $child.Value }
                        'REGION' { $regions += $child.Value }
                        'BLENDOP' { $blendOps += $child.Value }
                    }
                }
            }
            $material.Files = $files -join ' | '
            $material.Regions = $regions -join ' | '
            $material.BlendOps = $blendOps -join ' | '
        }
        elseif ($children.Count -eq 0 -and $node.Value -ne '') {
            $material = [MaterialReference]::new()
            $material.Type = 'MATERIAL_REFERENCE'
            $material.Name = $node.Value
        }
        else {
            $material = [MaterialUnclassified]::new()
            $material.Type = 'MATERIAL_UNCLASSIFIED'
        }
        $material.Index = $materials.Count
        $material.NodeIndex = $node.Index
        $material.Offset = $node.Offset
        $material.HexOffset = $node.HexOffset
        $material.Parent = $node.Parent
        $material.ParentIndex = $node.ParentIndex
        $material.Closed = $node.Closed
        $material.EndOffset = $node.Offset
        if ($node.Closed) {
            $material.EndOffset = $node.EndOffset
            $material.Length = $material.EndOffset - $material.Offset
        }
        $rawLength = if ($node.Closed) { $material.Length } else { $node.TagLength }
        if ($material.Offset -lt 0 -or $rawLength -lt 0 -or
            ([long]$material.Offset + $rawLength) -gt $Bytes.Length) {
            throw "Invalid material byte range at node $($node.Index)."
        }
        $material.RawTextEndOffset = $material.Offset + $rawLength
        $material.RawText = $rawEncoding.GetString($Bytes, $material.Offset, $rawLength)
        [void]$materials.Add($material)
    }
    return $materials.ToArray()
}

# A fixed export schema avoids losing definition-only columns when the first
# record is a reference. Blank columns do not add properties to the model.
function ConvertTo-OpenJadeMGMMaterialRows {
    param([AllowEmptyCollection()][array]$Materials)
    foreach ($material in $Materials) {
        $definition = $material -is [MaterialDefinition]
        [PSCustomObject][ordered]@{
            Index = $material.Index
            Offset = $material.Offset
            HexOffset = $material.HexOffset
            Type = $material.Type
            Name = $material.Name
            StageCount = $(if ($definition) { $material.StageCount } else { $null })
            Files = $(if ($definition) { $material.Files } else { '' })
            Regions = $(if ($definition) { $material.Regions } else { '' })
            BlendOps = $(if ($definition) { $material.BlendOps } else { '' })
            Length = $material.Length
            EndOffset = $material.EndOffset
            RawText = $material.RawText
            RawTextEndOffset = $material.RawTextEndOffset
            NodeIndex = $material.NodeIndex
            Parent = $material.Parent
            ParentIndex = $material.ParentIndex
            Closed = $material.Closed
        }
    }
}


function Get-OpenJadeMGM {
    <#
    .SYNOPSIS
        Reads observed MGM tag-like structures without modifying the source.
    .DESCRIPTION
        This is a byte-oriented research reader, not an XML validator or game
        runtime. Mismatched closing tags are reported without repairing the
        stack. RawText uses reversible Latin-1, not a claimed MGM text encoding.
    .PARAMETER Path
        Input MGM file. Relative paths use the current working directory.
    .EXAMPLE
        $document = Get-OpenJadeMGM -Path .\reports\menu\pop4common.mgm
        $document.Materials | Format-Table Type, Name, Offset
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $bytes = [IO.File]::ReadAllBytes($resolved)
    $encoding = [Text.Encoding]::GetEncoding(28591)
    $text = $encoding.GetString($bytes)
    $tags = New-Object 'System.Collections.Generic.List[object]'
    $nodes = New-Object 'System.Collections.Generic.List[object]'
    $stack = New-Object 'System.Collections.Generic.List[object]'
    $issues = New-Object 'System.Collections.Generic.List[object]'
    $recognizedOffsets = New-Object 'System.Collections.Generic.HashSet[int]'
    $pattern = '<(/?)([A-Za-z_][A-Za-z0-9_:\-.]*)(/?)>'
    foreach ($match in [regex]::Matches($text,$pattern)) {
        if ($match.Groups[1].Value -eq '/' -and $match.Groups[3].Value -eq '/') { continue }
        $tag = [pscustomobject]@{ Index=$tags.Count; Offset=$match.Index
            EndOffset=$match.Index+$match.Length; Length=$match.Length
            Name=$match.Groups[2].Value; Closing=($match.Groups[1].Value -eq '/')
            SelfClosing=($match.Groups[3].Value -eq '/')
            RawText=$match.Value }
        $tags.Add($tag)
        [void]$recognizedOffsets.Add($match.Index)
        if (-not $tag.Closing) {
            $parent = if ($stack.Count) { $stack[$stack.Count-1] } else { $null }
            $node = [pscustomobject][ordered]@{
                Index=$nodes.Count; Name=$tag.Name; Offset=$tag.Offset
                HexOffset=('0x{0:X8}' -f $tag.Offset)
                TagLength=$tag.Length; TagEndOffset=$tag.EndOffset
                ClosingOffset=-1; ClosingLength=0; Closed=$false; SelfClosing=$tag.SelfClosing
                EndOffset=$tag.Offset; Length=0
                ContentStart=$tag.EndOffset; ContentEnd=-1
                Parent=$(if ($null -ne $parent) { $parent.Name } else { '' })
                ParentIndex=$(if ($null -ne $parent) { $parent.Index } else { -1 })
                Depth=$stack.Count; HasChildren=$false; ChildCount=0; Value=''
                RawText=$tag.RawText; RawTextEndOffset=$tag.EndOffset
            }
            if ($null -ne $parent) { $parent.HasChildren=$true; $parent.ChildCount++ }
            $nodes.Add($node)
            if ($tag.SelfClosing) {
                $node.Closed=$true
                $node.EndOffset=$tag.EndOffset
                $node.Length=$tag.Length
                $node.ContentEnd=$tag.EndOffset
            } else { $stack.Add($node) }
            continue
        }
        if ($stack.Count -eq 0) {
            $issues.Add([pscustomobject]@{ Code='UnmatchedClosing'; Offset=$tag.Offset
                NodeIndex=-1; Message="Closing tag </$($tag.Name)> has no open node." })
            continue
        }
        $node = $stack[$stack.Count-1]
        if ($node.Name -cne $tag.Name) {
            $issues.Add([pscustomobject]@{ Code='MismatchedClosing'; Offset=$tag.Offset
                NodeIndex=$node.Index; Message="Expected </$($node.Name)> but observed </$($tag.Name)>; no repair performed." })
            continue
        }
        $node.ClosingOffset=$tag.Offset
        $node.ClosingLength=$tag.Length
        $node.Closed=$true
        $node.ContentEnd=$tag.Offset
        $node.EndOffset=$tag.EndOffset
        $node.Length=$node.EndOffset-$node.Offset
        $node.RawText=$text.Substring($node.Offset,$node.Length)
        $node.RawTextEndOffset=$node.EndOffset
        if (-not $node.HasChildren) {
            $node.Value=$text.Substring($node.ContentStart,$node.ContentEnd-$node.ContentStart).Trim([char[]]@(0,9,10,13,32))
        }
        $stack.RemoveAt($stack.Count-1)
    }
    foreach ($node in $stack) {
        $issues.Add([pscustomobject]@{ Code='UnclosedNode'; Offset=$node.Offset
            NodeIndex=$node.Index; Message="No matching closing tag recorded for <$($node.Name)>." })
    }
    # Unsupported angle-bracket candidates are observations, not XML errors.
    foreach ($candidate in [regex]::Matches($text,'</?[A-Za-z_][^<>]*>')) {
        if (-not $recognizedOffsets.Contains($candidate.Index)) {
            $issues.Add([pscustomobject]@{ Code='UnsupportedTagCandidate'; Offset=$candidate.Index
                NodeIndex=-1; Message='Angle-bracket candidate is outside the supported bare-tag grammar.' })
        }
    }
    $materials = @(Get-OpenJadeMGMMaterials -Nodes $nodes.ToArray() -Bytes $bytes)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { $sha256 = [BitConverter]::ToString($hash.ComputeHash($bytes)).Replace('-','') }
    finally { $hash.Dispose() }
    $summary = [pscustomobject][ordered]@{
        FileName=[IO.Path]::GetFileName($resolved); FileSize=$bytes.Length; SHA256=$sha256
        TagCount=$tags.Count; NodeCount=$nodes.Count
        SelfClosingCount=@($nodes | Where-Object SelfClosing).Count
        RootCount=@($nodes | Where-Object ParentIndex -eq -1).Count
        ClosedNodeCount=@($nodes | Where-Object Closed).Count
        DefinitionCount=@($materials | Where-Object Type -eq 'MATERIAL_DEFINITION').Count
        ReferenceCount=@($materials | Where-Object Type -eq 'MATERIAL_REFERENCE').Count
        UnclassifiedCount=@($materials | Where-Object Type -eq 'MATERIAL_UNCLASSIFIED').Count
        DiagnosticCount=$issues.Count
    }
    [pscustomobject]@{ Path=$resolved; Summary=$summary; Bytes=$bytes
        Tags=$tags.ToArray(); Nodes=$nodes.ToArray(); Materials=$materials
        Diagnostics=@($issues | Sort-Object Offset,Code) }
}

function Export-OpenJadeMGMReport {
    <#
    .SYNOPSIS
        Writes a readable report and structured tables to a new directory.
    .PARAMETER Document
        Result of Get-OpenJadeMGM.
    .PARAMETER OutputDirectory
        New report directory. Existing roots and the game directory are refused.
    .EXAMPLE
        Get-OpenJadeMGM .\reports\menu\pop4common.mgm |
            Export-OpenJadeMGMReport -OutputDirectory .\reports\common-analysis
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory,ValueFromPipeline)][psobject]$Document,
        [Parameter(Mandatory)][string]$OutputDirectory)
    process {
        $root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
        $game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
        if ($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or
            $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'The game directory is read-only.' }
        if (Test-Path -LiteralPath $root) { throw "Report directory already exists: $root" }
        $ancestor=$root
        while ($ancestor) {
            if (Test-Path -LiteralPath $ancestor) {
                $item=Get-Item -LiteralPath $ancestor -Force -ErrorAction Stop
                if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Report path contains a reparse point.' }
            }
            $ancestor=[IO.Path]::GetDirectoryName($ancestor)
        }
        [void][IO.Directory]::CreateDirectory($root)
        $utf8=New-Object Text.UTF8Encoding($false)
        [IO.File]::WriteAllText((Join-Path $root 'summary.json'),($Document.Summary | ConvertTo-Json),$utf8)
        # Serialize arrays explicitly, including [] for empty results.
        [IO.File]::WriteAllText((Join-Path $root 'diagnostics.json'),(ConvertTo-Json -InputObject @($Document.Diagnostics) -Depth 4),$utf8)
        $tables=@(
            @{Name='tags'; Rows=@($Document.Tags); Columns=@('Index','Offset','EndOffset','Length','Name','Closing','SelfClosing','RawText')},
            @{Name='nodes'; Rows=@($Document.Nodes); Columns=@('Index','Name','Offset','EndOffset','Length','Closed','SelfClosing','ParentIndex','Parent','Depth','Value','ContentStart','ContentEnd','RawTextEndOffset','RawText')},
            @{Name='materials'; Rows=@(ConvertTo-OpenJadeMGMMaterialRows -Materials $Document.Materials); Columns=@('Index','Offset','HexOffset','Type','Name','StageCount','Files','Regions','BlendOps','Length','EndOffset','RawText','RawTextEndOffset','NodeIndex','Parent','ParentIndex','Closed')}
        )
        foreach ($table in $tables) {
            $path=Join-Path $root ($table.Name+'.csv')
            if ($table.Rows.Count) { $table.Rows | Select-Object $table.Columns | Export-Csv -LiteralPath $path -NoTypeInformation -Encoding UTF8 }
            else { [IO.File]::WriteAllText($path,('"'+($table.Columns -join '","')+'"'+"`r`n"),$utf8) }
        }
        $writer=New-Object IO.StreamWriter((Join-Path $root 'structure.txt'),$false,$utf8)
        try {
            $writer.WriteLine('OpenJade MGM structural observations')
            $writer.WriteLine(($Document.Summary | Format-List | Out-String).Trim())
            $writer.WriteLine('Offsets are byte offsets; end offsets are exclusive.')
            $writer.WriteLine('Raw text is reversible Latin-1. Displayed values are JSON-escaped.')
            $writer.WriteLine('Closed means a matching pair was recorded; it does not validate its descendants.')
            $writer.WriteLine('=== NODE TREE (opening order) ===')
            foreach ($node in $Document.Nodes) {
                $value=ConvertTo-Json -InputObject ([string]$node.Value) -Compress
                $writer.WriteLine(('{0}[{1}] <{2}> offset={3} end={4} closed={5} parent={6} value={7}' -f
                    ('  '*[Math]::Min($node.Depth,40)),$node.Index,$node.Name,$node.Offset,$node.EndOffset,$node.Closed,$node.ParentIndex,$value))
            }
            $writer.WriteLine('=== MATERIALS ===')
            foreach ($material in $Document.Materials) {
                $writer.WriteLine(('[{0}] {1} name={2} offset={3} end={4} parent={5}' -f $material.Index,$material.Type,
                    (ConvertTo-Json -InputObject $material.Name -Compress),$material.Offset,$material.EndOffset,$material.ParentIndex))
            }
            $writer.WriteLine('=== DIAGNOSTICS ===')
            foreach ($issue in $Document.Diagnostics) { $writer.WriteLine(('{0} at {1}: {2}' -f $issue.Code,$issue.Offset,$issue.Message)) }
        }
        finally { $writer.Dispose() }
        [pscustomobject]@{ OutputDirectory=$root; ReportPath=(Join-Path $root 'structure.txt') }
    }
}

Export-ModuleMember -Function Get-OpenJadeMGM,Export-OpenJadeMGMReport
