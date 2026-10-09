#requires -Version 5.1
Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'OpenJade.MGM.psm1')

function Get-MGMLinkInventory {
    param([string]$Root)
    $files=New-Object 'System.Collections.Generic.List[object]'
    $skipped=New-Object 'System.Collections.Generic.List[string]'
    $directories=New-Object 'System.Collections.Generic.Stack[string]'
    $directories.Push($Root)
    while ($directories.Count) {
        foreach ($item in Get-ChildItem -LiteralPath $directories.Pop() -Force -ErrorAction Stop) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                $skipped.Add($item.FullName)
            } elseif ($item.PSIsContainer) { $directories.Push($item.FullName) }
            else {
                $files.Add([pscustomobject]@{ RelativePath=$item.FullName.Substring($Root.TrimEnd('\').Length+1).Replace('\','/')
                    FullPath=$item.FullName; Length=$item.Length })
            }
        }
    }
    [pscustomobject]@{ Files=$files.ToArray(); Skipped=$skipped.ToArray() }
}

function Get-MGMFileMatch {
    param([string]$Value,[array]$Files,[switch]$Font)
    $relative=$Value.Replace('\','/')
    if ($relative.StartsWith('//') -or $relative.Contains(':')) {
        return [pscustomobject]@{Status='UnsafePath'; Candidates=@(); Evidence='Drive or network path is not a resource-relative path.'}
    }
    # A single leading separator is interpreted relative to the explicit asset root.
    $relative=$relative.TrimStart('/')
    foreach ($part in ($relative -split '/')) {
        if ([string]::IsNullOrWhiteSpace($part) -or $part -eq '.' -or $part -eq '..' -or
            $part.EndsWith('.') -or $part.EndsWith(' ') -or
            $part.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or
            $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
            return [pscustomobject]@{Status='UnsafePath'; Candidates=@(); Evidence='Unsafe or empty resource path component.'}
        }
    }
    $matches=@($Files | Where-Object { [string]::Equals($_.RelativePath,$relative,[StringComparison]::OrdinalIgnoreCase) })
    $status=if ($matches.Count -eq 0) {'MissingFile'} elseif ($matches.Count -gt 1) {'AmbiguousFile'} elseif ($Font) {'FontFileCandidate'} elseif ($matches[0].RelativePath -ceq $relative) {'FileFound'} else {'CaseInsensitiveFileMatch'}
    [pscustomobject]@{ Status=$status; Candidates=$matches
        Evidence=$(if ($Font) {'Candidate convention: fonts/<declared name>.mft; MFT contents not decoded.'} else {'Path matched relative to AssetRoot; case differences recorded. File content not decoded.'}) }
}

function Get-OpenJadeMGMLinks {
    <#
    .SYNOPSIS
        Links MGM material/font names and resource files using explicit evidence.
    .DESCRIPTION
        Resolves exact names inside this document only. Case-only name matches
        remain candidates. Maps texture paths relative to AssetRoot and lists
        fonts/<name>.mft as candidates, not decoded or validated fonts. No input
        is modified. A document with structural diagnostics is not resolved.
    .PARAMETER Path
        Input MGM file.
    .PARAMETER AssetRoot
        Extracted menu resource directory containing texture and fonts folders.
    .EXAMPLE
        Get-OpenJadeMGMLinks -Path .\reports\data\menu\pop4common.mgm -AssetRoot .\reports\data\menu
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path,[Parameter(Mandatory)][string]$AssetRoot)
    $root=(Resolve-Path -LiteralPath $AssetRoot -ErrorAction Stop).ProviderPath
    if (-not (Test-Path -LiteralPath $root -PathType Container)) { throw 'AssetRoot must be a directory.' }
    $ancestor=$root
    while ($ancestor) {
        if (((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Asset root contains a reparse point.' }
        $ancestor=[IO.Path]::GetDirectoryName($ancestor)
    }
    $inventory=Get-MGMLinkInventory $root
    $document=Get-OpenJadeMGM -Path $Path
    $children=@{}
    foreach ($node in $document.Nodes) {
        if (-not $children.ContainsKey($node.ParentIndex)) { $children[$node.ParentIndex]=New-Object 'System.Collections.Generic.List[object]' }
        $children[$node.ParentIndex].Add($node)
    }
    $definitions=@($document.Materials | Where-Object Type -eq 'MATERIAL_DEFINITION')
    $fonts=@($document.Nodes | Where-Object { $_.Name -ceq 'Pixmap' -and $_.Parent -ceq 'FONTS' })
    $fontDefinitions=@(foreach ($font in $fonts) {
        $names=@($children[$font.Index] | Where-Object { $null -ne $_ -and $_.Name -ceq 'NAME' })
        foreach ($name in $names) { [pscustomobject]@{Name=$name.Value; NodeIndex=$font.Index; Offset=$font.Offset; NameNode=$name} }
    })
    $links=New-Object 'System.Collections.Generic.List[object]'
    $healthy=$document.Diagnostics.Count -eq 0
    # Every edge points to a source node; resolved names also point to a target node.
    foreach ($node in $document.Nodes) {
        $kind=''; $value=$node.Value; $targets=@(); $fileMatch=$null
        if ($node.Name -ceq 'MATERIAL' -and -not $node.HasChildren -and $value -ne '') {
            $kind='MaterialReference'; $targets=$definitions
        } elseif ($node.Name -ceq 'FONT' -and -not $node.HasChildren) {
            $kind='FontReference'; $targets=$fontDefinitions
        } elseif ($node.Name -ceq 'FILE' -and $node.Parent -ceq 'STAGE') {
            $kind='TextureFile'
        } elseif ($node.Name -ceq 'NAME' -and $node.Parent -ceq 'Pixmap' -and
            @($fontDefinitions | Where-Object { $_.NameNode.Index -eq $node.Index }).Count) {
            $kind='FontFile'; $value=$node.Value
        } else { continue }
        $owner=if ($node.ParentIndex -ge 0) {$document.Nodes[$node.ParentIndex]} else {$null}
        if ($kind -eq 'TextureFile' -and $null -ne $owner -and $owner.ParentIndex -ge 0) { $owner=$document.Nodes[$owner.ParentIndex] }
        $ownerNames=@(if ($null -ne $owner) { $children[$owner.Index] | Where-Object { $null -ne $_ -and $_.Name -ceq 'NAME' } })
        $row=[pscustomobject][ordered]@{
            LinkId=$links.Count; Kind=$kind; SourceNodeIndex=$node.Index; SourceOffset=$node.Offset
            OwnerNodeIndex=$(if ($null -ne $owner) {$owner.Index} else {-1})
            OwnerType=$(if ($null -ne $owner) {$owner.Name} else {''})
            OwnerName=$(if ($ownerNames.Count -eq 1) {$ownerNames[0].Value} else {''})
            Value=$value; Status='UncertainStructure'; TargetNodeIndex=-1; TargetOffset=-1
            TargetPath=''; CandidateCount=0; CandidatesJson='[]'; Evidence='Structural diagnostics prevent resolution.'
        }
        if ($healthy -and $node.Closed) {
            if ($kind -in @('MaterialReference','FontReference')) {
                $exact=@($targets | Where-Object { $_.Name -ceq $value })
                $candidates=$exact
                if ($exact.Count -eq 1 -and $value -ne '') {
                    $row.Status='ResolvedName'; $row.TargetNodeIndex=$exact[0].NodeIndex; $row.TargetOffset=$exact[0].Offset
                    $row.Evidence='Unique exact name in this document; runtime scope is not inferred.'
                } elseif ($exact.Count -gt 1) {
                    $row.Status='AmbiguousDefinition'; $row.Evidence='Multiple exact names; no target chosen.'
                } else {
                    $candidates=@($targets | Where-Object { $_.Name -ieq $value -and $value -ne '' })
                    $row.Status=if ($candidates.Count) {'CaseMismatchCandidate'} else {'MissingDefinition'}
                    $row.Evidence='No exact local definition; cross-document lookup is not attempted.'
                }
                $row.CandidateCount=$candidates.Count
                $row.CandidatesJson=ConvertTo-Json -InputObject @($candidates | Select-Object Name,NodeIndex,Offset) -Compress
            } else {
                $resource=if ($kind -eq 'FontFile') {'fonts/'+$value+'.mft'} else {$value}
                # Font names must be plain names, never directory paths.
                if ($kind -eq 'FontFile' -and ($value.IndexOfAny([char[]]'\/') -ge 0 -or [string]::IsNullOrWhiteSpace($value))) {
                    $fileMatch=[pscustomobject]@{Status='UnsafePath';Candidates=@();Evidence='Font name is empty or contains a path separator.'}
                } else { $fileMatch=Get-MGMFileMatch -Value $resource -Files $inventory.Files -Font:($kind -eq 'FontFile') }
                $row.Status=$fileMatch.Status; $row.Evidence=$fileMatch.Evidence; $row.CandidateCount=$fileMatch.Candidates.Count
                $row.CandidatesJson=ConvertTo-Json -InputObject @($fileMatch.Candidates | Select-Object RelativePath,FullPath) -Compress
                if ($fileMatch.Candidates.Count -eq 1) { $row.TargetPath=$fileMatch.Candidates[0].FullPath }
            }
        }
        $links.Add($row)
    }
    $elements=New-Object 'System.Collections.Generic.List[object]'
    foreach ($reference in @($links | Where-Object { $_.Kind -in @('MaterialReference','FontReference') })) {
        $resources=@()
        if ($reference.Status -eq 'ResolvedName') {
            $resourceKind=if ($reference.Kind -eq 'MaterialReference') {'TextureFile'} else {'FontFile'}
            $resources=@($links | Where-Object { $_.Kind -eq $resourceKind -and $_.OwnerNodeIndex -eq $reference.TargetNodeIndex })
        }
        if (-not $resources.Count) { $resources=@($null) }
        foreach ($resource in $resources) {
            $elements.Add([pscustomobject][ordered]@{
                ElementNodeIndex=$reference.OwnerNodeIndex; ElementType=$reference.OwnerType; ElementName=$reference.OwnerName
                ReferenceNodeIndex=$reference.SourceNodeIndex; ReferenceOffset=$reference.SourceOffset; ReferenceKind=$reference.Kind
                ReferenceName=$reference.Value; ReferenceStatus=$reference.Status; DefinitionNodeIndex=$reference.TargetNodeIndex
                ResourceNodeIndex=$(if ($null -ne $resource) {$resource.SourceNodeIndex} else {-1})
                ResourceStatus=$(if ($null -ne $resource) {$resource.Status} elseif ($reference.Status -eq 'ResolvedName') {'NoFileDeclaration'} else {'UnresolvedReference'})
                ResourcePath=$(if ($null -ne $resource) {$resource.TargetPath} else {''})
            })
        }
    }
    $summary=[pscustomobject]@{
        FileName=$document.Summary.FileName; SHA256=$document.Summary.SHA256; AssetRoot=$root
        StructuralDiagnostics=$document.Diagnostics.Count; AssetCount=$inventory.Files.Count; SkippedReparsePoints=$inventory.Skipped.Count
        MaterialReferences=@($links | Where-Object Kind -eq MaterialReference).Count
        FontReferences=@($links | Where-Object Kind -eq FontReference).Count
        TextureDeclarations=@($links | Where-Object Kind -eq TextureFile).Count
        FontDeclarations=@($links | Where-Object Kind -eq FontFile).Count
        ResolvedNames=@($links | Where-Object Status -eq ResolvedName).Count
        FontFileCandidates=@($links | Where-Object Status -eq FontFileCandidate).Count
        IncompleteChains=@($elements | Where-Object ResourceStatus -eq NoFileDeclaration).Count
        AttentionCount=(@($links | Where-Object { $_.Status -notin @('ResolvedName','FileFound','CaseInsensitiveFileMatch','FontFileCandidate') }).Count + @($elements | Where-Object ResourceStatus -eq NoFileDeclaration).Count)
    }
    [pscustomobject]@{ Document=$document; Summary=$summary; Links=$links.ToArray(); Elements=$elements.ToArray()
        Assets=$inventory.Files; SkippedPaths=$inventory.Skipped }
}

function Export-OpenJadeMGMLinks {
    <#
    .SYNOPSIS
        Writes structural reports plus resource links and element chains.
    .PARAMETER Analysis
        Result of Get-OpenJadeMGMLinks.
    .PARAMETER OutputDirectory
        New directory for reports. No existing report is overwritten.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][psobject]$Analysis,[Parameter(Mandatory)][string]$OutputDirectory)
    $report=Export-OpenJadeMGMReport -Document $Analysis.Document -OutputDirectory $OutputDirectory
    $root=$report.OutputDirectory
    $utf8=New-Object Text.UTF8Encoding($false)
    $tables=@(
        @{Name='links'; Rows=@($Analysis.Links); Columns=@('LinkId','Kind','SourceNodeIndex','SourceOffset','OwnerNodeIndex','OwnerType','OwnerName','Value','Status','TargetNodeIndex','TargetOffset','TargetPath','CandidateCount','CandidatesJson','Evidence')},
        @{Name='elements'; Rows=@($Analysis.Elements); Columns=@('ElementNodeIndex','ElementType','ElementName','ReferenceNodeIndex','ReferenceOffset','ReferenceKind','ReferenceName','ReferenceStatus','DefinitionNodeIndex','ResourceNodeIndex','ResourceStatus','ResourcePath')},
        @{Name='assets'; Rows=@($Analysis.Assets); Columns=@('RelativePath','FullPath','Length')}
    )
    foreach ($table in $tables) {
        $path=Join-Path $root ($table.Name+'.csv')
        if ($table.Rows.Count) { $table.Rows | Select-Object $table.Columns | Export-Csv -LiteralPath $path -NoTypeInformation -Encoding UTF8 }
        else { [IO.File]::WriteAllText($path,('"'+($table.Columns -join '","')+'"'+"`r`n"),$utf8) }
    }
    [IO.File]::WriteAllText((Join-Path $root 'links-summary.json'),($Analysis.Summary | ConvertTo-Json),$utf8)
    [IO.File]::WriteAllText((Join-Path $root 'skipped-paths.json'),(ConvertTo-Json -InputObject @($Analysis.SkippedPaths)),$utf8)
    $writer=New-Object IO.StreamWriter((Join-Path $root 'references.txt'),$false,$utf8)
    try {
        $writer.WriteLine('OpenJade MGM resource links')
        $writer.WriteLine(($Analysis.Summary | Format-List | Out-String).Trim())
        $writer.WriteLine('Name resolution is local to this file. Font files are filename candidates only.')
        $writer.WriteLine('File existence is not evidence of successful decoding or rendering.')
        foreach ($element in $Analysis.Elements) {
            $writer.WriteLine(('{0} node {1}, name={2}, reference={3} at byte {4}' -f $element.ElementType,$element.ElementNodeIndex,
                (ConvertTo-Json -InputObject $element.ElementName -Compress),(ConvertTo-Json -InputObject $element.ReferenceName -Compress),$element.ReferenceOffset))
            $writer.WriteLine(('  {0} -> definition {1} -> {2}: {3}' -f $element.ReferenceStatus,$element.DefinitionNodeIndex,$element.ResourceStatus,$element.ResourcePath))
        }
        $writer.WriteLine('=== LINKS REQUIRING ATTENTION ===')
        foreach ($link in @($Analysis.Links | Where-Object { $_.Status -notin @('ResolvedName','FileFound','CaseInsensitiveFileMatch','FontFileCandidate') })) {
            $writer.WriteLine(('{0} at byte {1}: {2} ({3})' -f $link.Kind,$link.SourceOffset,$link.Status,(ConvertTo-Json -InputObject $link.Value -Compress)))
        }
        foreach ($element in @($Analysis.Elements | Where-Object ResourceStatus -eq NoFileDeclaration)) {
            $writer.WriteLine(('Reference at byte {0}: definition {1} has no file declaration.' -f $element.ReferenceOffset,$element.DefinitionNodeIndex))
        }
    } finally { $writer.Dispose() }
    [pscustomobject]@{ OutputDirectory=$root; ReportPath=(Join-Path $root 'references.txt') }
}

Export-ModuleMember -Function Get-OpenJadeMGMLinks,Export-OpenJadeMGMLinks
