#requires -Version 5.1
Set-StrictMode -Version Latest

function Read-OpenJadeBFIndex {
    param([System.IO.BinaryReader]$Reader)
    $stream = $Reader.BaseStream
    if ($stream.Length -lt 4) { throw 'BF header is truncated.' }
    $headerSize = $Reader.ReadUInt32()
    $dataStart = 4L + $headerSize
    if ($dataStart -gt $stream.Length) { throw 'BF header exceeds the file size.' }
    $entries = New-Object 'System.Collections.Generic.List[object]'
    $names = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    while ($stream.Position -lt $dataStart) {
        $entryStart = $stream.Position
        if ($dataStart - $entryStart -lt 20) { throw 'BF entry header is truncated.' }
        $entryOffset = $Reader.ReadUInt32()
        $offset = $Reader.ReadUInt32()
        $length = $Reader.ReadUInt32()
        $unknown = $Reader.ReadUInt32()
        $nameLength = $Reader.ReadUInt32()
        if ($nameLength -eq 0 -or $nameLength -gt ($dataStart - $stream.Position) -or $nameLength -gt [int]::MaxValue) {
            throw 'Invalid BF filename length.'
        }
        $nameBytes = $Reader.ReadBytes([int]$nameLength)
        # The supported filename subset is ASCII. Reject other bytes instead of
        # silently replacing them; the general filename encoding is unverified.
        foreach ($b in $nameBytes) { if ($b -gt 127) { throw 'Unsupported non-ASCII BF filename.' } }
        $name = [Text.Encoding]::ASCII.GetString($nameBytes).TrimEnd([char]0)
        if ([string]::IsNullOrWhiteSpace($name) -or $name.Contains([string][char]0)) { throw 'Invalid BF filename.' }
        if (-not $names.Add($name)) { throw "Duplicate BF filename: $name" }
        $start = $dataStart + [long]$offset
        if ($start -gt $stream.Length -or [long]$length -gt ($stream.Length - $start)) {
            throw "BF entry exceeds the file size: $name"
        }
        $entries.Add([pscustomobject][ordered]@{
            Index = $entries.Count; FileName = $name
            EntryHeaderAddress = $entryStart; EntryOffset = $entryOffset
            DataOffset = $offset; DataLength = $length; Unknown = $unknown
            FileNameLength = $nameLength
            AbsoluteDataStart = $start; AbsoluteDataEnd = $start + [long]$length
        })
    }
    [pscustomobject]@{ HeaderSize = $headerSize; DataStart = $dataStart
        FileSize = $stream.Length; Entries = $entries.ToArray() }
}

function Get-OpenJadeBFArchive {
    <#
    .SYNOPSIS
        Reads a supported BF archive index without modifying the archive.
    .PARAMETER Path
        Path to the BF archive. Relative paths use the current directory.
    .EXAMPLE
        Get-OpenJadeBFArchive -Path .\game\TSoT-GOG\POPData.BF
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path)
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $stream = [IO.File]::Open($resolved, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::Read)
    $reader = New-Object IO.BinaryReader($stream)
    try {
        $index = Read-OpenJadeBFIndex $reader
        $index | Add-Member -NotePropertyName Path -NotePropertyValue $resolved
        $index
    }
    finally { $reader.Dispose() }
}

function Get-OpenJadeSafeDestination {
    param([string]$Root, [string]$Name)
    if ([IO.Path]::IsPathRooted($Name)) { throw "Rooted archive path: $Name" }
    $parts = $Name -split '[\\/]'
    foreach ($part in $parts) {
        if ([string]::IsNullOrWhiteSpace($part) -or $part -eq '.' -or $part -eq '..' -or
            $part.EndsWith('.') -or $part.EndsWith(' ') -or
            $part.IndexOfAny([IO.Path]::GetInvalidFileNameChars()) -ge 0 -or
            $part -match '^(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)') {
            throw "Unsafe archive path: $Name"
        }
    }
    $destination = [IO.Path]::GetFullPath((Join-Path $Root ($parts -join '\')))
    $prefix = $Root.TrimEnd('\') + '\'
    if (-not $destination.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Output escapes its root.' }
    # Existing junctions and symbolic links must not redirect writes.
    $current = $destination
    while ($current) {
        if (Test-Path -LiteralPath $current) {
            $item = Get-Item -LiteralPath $current -Force -ErrorAction Stop
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse point in output path: $current" }
        }
        $current = [IO.Path]::GetDirectoryName($current)
    }
    $destination
}

function Export-OpenJadeBFEntry {
    <#
    .SYNOPSIS
        Extracts one named entry or all entries into a new output directory.
    .DESCRIPTION
        Reads the archive without changing it. Refuses existing output roots,
        unsafe entry paths and writes inside this project's reference folders.
        A failed I/O operation may leave partial output for inspection.
    .PARAMETER Path
        Path to the input BF archive.
    .PARAMETER Entry
        Exact internal filename, matched without case sensitivity.
    .PARAMETER All
        Extract all archive entries.
    .PARAMETER OutputDirectory
        New destination directory. Existing directories are never overwritten.
    .EXAMPLE
        Export-OpenJadeBFEntry -Path .\game\TSoT-GOG\POPData.BF -Entry gamepads.dat -OutputDirectory .\reports\gamepads
    #>
    [CmdletBinding(DefaultParameterSetName='Single')]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory,ParameterSetName='Single')][ValidateNotNullOrEmpty()][string]$Entry,
        [Parameter(Mandatory,ParameterSetName='All')][switch]$All,
        [Parameter(Mandatory)][string]$OutputDirectory
    )
    $resolved = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $root = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
    $projectRoot = Split-Path $PSScriptRoot -Parent
    foreach ($folder in @('game')) {
        $protected = Join-Path $projectRoot $folder
        if ($root.Equals($protected,[StringComparison]::OrdinalIgnoreCase) -or
            $root.StartsWith($protected + '\',[StringComparison]::OrdinalIgnoreCase)) { throw "Protected reference directory: $root" }
    }
    if (Test-Path -LiteralPath $root) { throw "Output directory already exists: $root" }
    $stream = [IO.File]::Open($resolved,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::Read)
    $reader = New-Object IO.BinaryReader($stream)
    try {
        $index = Read-OpenJadeBFIndex $reader
        $selected = @($index.Entries | Where-Object { $PSCmdlet.ParameterSetName -eq 'All' -or $_.FileName -ieq $Entry })
        if ($PSCmdlet.ParameterSetName -eq 'Single' -and $selected.Count -ne 1) { throw "Entry not found: $Entry" }
        $destinations = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
        $plan = @($selected | ForEach-Object {
            $destination = Get-OpenJadeSafeDestination $root $_.FileName
            if (-not $destinations.Add($destination)) { throw "Output name collision: $destination" }
            [pscustomobject]@{ Entry = $_; Destination = $destination }
        })
        foreach ($item in $plan) {
            $parent = [IO.Path]::GetDirectoryName($item.Destination)
            while ($parent.Length -gt $root.Length) {
                if ($destinations.Contains($parent)) { throw "File/directory collision: $parent" }
                $parent = [IO.Path]::GetDirectoryName($parent)
            }
        }
        [void][IO.Directory]::CreateDirectory($root)
        $buffer = New-Object byte[] 65536
        foreach ($item in $plan) {
            [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($item.Destination))
            $output = [IO.File]::Open($item.Destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
            try {
                $stream.Position = $item.Entry.AbsoluteDataStart
                $remaining = [long]$item.Entry.DataLength
                while ($remaining -gt 0) {
                    $read = $stream.Read($buffer,0,[int][Math]::Min($remaining,$buffer.Length))
                    if ($read -eq 0) { throw 'Unexpected end of archive during extraction.' }
                    $output.Write($buffer,0,$read)
                    $remaining -= $read
                }
            }
            finally { $output.Dispose() }
            [pscustomobject]@{ FileName = $item.Entry.FileName; Length = $item.Entry.DataLength
                OutputPath = $item.Destination; SHA256 = (Get-FileHash -LiteralPath $item.Destination -Algorithm SHA256).Hash }
        }
    }
    finally { $reader.Dispose() }
}

Export-ModuleMember -Function Get-OpenJadeBFArchive, Export-OpenJadeBFEntry
