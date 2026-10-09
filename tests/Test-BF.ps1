#requires -Version 5.1
<#
.SYNOPSIS
    Runs synthetic BF regressions and optional local game-data comparisons.
.PARAMETER GameArchive
    Optional BF archive to extract and check without changing the input.
.EXAMPLE
    .\tests\Test-BF.ps1
#>
[CmdletBinding()]
param([string]$GameArchive)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
Import-Module (Join-Path $project 'src/OpenJade.BF.psm1') -Force
$run = Join-Path $project ('reports/bf-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks = New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition, [string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $checks.Add($Name)
}
function Assert-Throws([scriptblock]$Action, [string]$Name) {
    $thrown = $false
    try { & $Action | Out-Null } catch { $thrown = $true }
    Assert $thrown $Name
}
function New-Fixture([string]$Path, [array]$Entries) {
    $headerSize = 0
    foreach ($e in $Entries) { $headerSize += 20 + [Text.Encoding]::ASCII.GetByteCount($e.Name) + 1 }
    $stream = [IO.File]::Create($Path)
    $writer = New-Object IO.BinaryWriter($stream)
    try {
        $writer.Write([uint32]$headerSize)
        $dataOffset = 0
        foreach ($e in $Entries) {
            $writer.Write([uint32]($stream.Position - 4))
            $writer.Write([uint32]$dataOffset)
            $writer.Write([uint32]$e.Data.Length)
            $writer.Write([uint32]0)
            $name = [Text.Encoding]::ASCII.GetBytes($e.Name + [char]0)
            $writer.Write([uint32]$name.Length)
            $writer.Write([byte[]]$name)
            $dataOffset += $e.Data.Length
        }
        foreach ($e in $Entries) { $writer.Write([byte[]]$e.Data) }
    }
    finally { $writer.Dispose() }
}
$fixture = Join-Path $run 'fixture.bf'
$payload = [byte[]](0,1,127,128,255)
New-Fixture $fixture @(
    @{ Name='nested/data.bin'; Data=$payload },
    @{ Name='empty.bin'; Data=[byte[]]@() }
)
$hashBefore = (Get-FileHash $fixture).Hash
$archive = Get-OpenJadeBFArchive $fixture
Assert ($archive.Entries.Count -eq 2) 'Index entry count'
Assert ($archive.DataStart -eq 70) 'Independent expected data start'
Assert ($archive.Entries[0].AbsoluteDataStart -eq 70 -and $archive.Entries[0].AbsoluteDataEnd -eq 75) 'Exact exclusive offsets'
Assert ($archive.Entries[1].DataLength -eq 0) 'Empty entry size'
$allRoot = Join-Path $run 'all'
$all = @(Export-OpenJadeBFEntry -Path $fixture -All -OutputDirectory $allRoot)
Assert ($all.Count -eq 2) 'All-entry extraction count'
Assert ([Convert]::ToBase64String([IO.File]::ReadAllBytes($all[0].OutputPath)) -eq [Convert]::ToBase64String($payload)) 'Exact binary extraction'
Assert ((Get-Item $all[1].OutputPath).Length -eq 0) 'Empty file extraction'
$single = @(Export-OpenJadeBFEntry -Path $fixture -Entry 'NESTED/DATA.BIN' -OutputDirectory (Join-Path $run 'single'))
Assert ($single.Count -eq 1 -and $single[0].SHA256 -eq $all[0].SHA256) 'Named case-insensitive extraction'
Assert-Throws { Export-OpenJadeBFEntry -Path $fixture -All -OutputDirectory $allRoot } 'Existing output is refused'
Assert-Throws { Export-OpenJadeBFEntry -Path $fixture -Entry missing -OutputDirectory (Join-Path $run 'missing') } 'Missing entry is refused'
Assert (-not (Test-Path (Join-Path $run 'missing'))) 'Missing entry creates no output'
Assert-Throws { Export-OpenJadeBFEntry -Path $fixture -All -OutputDirectory (Join-Path $project 'game/forbidden-test') } 'Game directory is protected'
Assert ((Get-FileHash $fixture).Hash -eq $hashBefore) 'Synthetic input is unchanged'
$bad = Join-Path $run 'bad.bf'
foreach ($bytes in @([byte[]](1,2,3), [byte[]](255,255,255,255))) {
    [IO.File]::WriteAllBytes($bad,$bytes)
    Assert-Throws { Get-OpenJadeBFArchive $bad } 'Truncated or oversized header is refused'
}
$original = [IO.File]::ReadAllBytes($fixture)
foreach ($mutation in @(@{Offset=4;Value=[uint32]0}, @{Offset=8;Value=[uint32]::MaxValue}, @{Offset=12;Value=[uint32]::MaxValue}, @{Offset=20;Value=[uint32]::MaxValue})) {
    $bytes = [byte[]]$original.Clone()
    if ($mutation.Offset -eq 4) {
        # Declare a header too short to contain the first fixed entry header.
        [BitConverter]::GetBytes([uint32]19).CopyTo($bytes,0)
    } else { [BitConverter]::GetBytes($mutation.Value).CopyTo($bytes,$mutation.Offset) }
    [IO.File]::WriteAllBytes($bad,$bytes)
    Assert-Throws { Get-OpenJadeBFArchive $bad } 'Invalid entry range is refused'
}
foreach ($name in @('../escape.bin','C:\escape.bin','nested/../../escape.bin','NUL','file:stream','trailing.')) {
    New-Fixture $bad @(@{Name=$name;Data=$payload})
    $output = Join-Path $run ([guid]::NewGuid().ToString('N'))
    Assert-Throws { Export-OpenJadeBFEntry -Path $bad -All -OutputDirectory $output } "Unsafe path refused: $name"
    Assert (-not (Test-Path $output)) 'Unsafe path creates no output'
}
foreach ($names in @(@('a','A'), @('a','a/b'), @('a/b','a\b'))) {
    New-Fixture $bad @(@{Name=$names[0];Data=$payload},@{Name=$names[1];Data=$payload})
    Assert-Throws { Export-OpenJadeBFEntry -Path $bad -All -OutputDirectory (Join-Path $run 'collision') } 'Name collision refused'
}
[IO.File]::WriteAllBytes($bad,[byte[]](0,0,0,0))
Assert (@((Get-OpenJadeBFArchive $bad).Entries).Count -eq 0) 'Empty index is supported'
$wrapperEntries = @(& (Join-Path $project 'tools/Read-BF.ps1') -Path $fixture)
Assert ($wrapperEntries.Count -eq 2) 'Reader command works'
$wrapperExport = @(& (Join-Path $project 'tools/Extract-BF.ps1') -Path $fixture -Entry empty.bin -OutputDirectory (Join-Path $run 'wrapper'))
Assert ($wrapperExport.Count -eq 1 -and $wrapperExport[0].Length -eq 0) 'Extractor command works'
$realResult = $null
if ($GameArchive) {
    $before = (Get-FileHash -LiteralPath $GameArchive).Hash
    $real = Get-OpenJadeBFArchive -Path $GameArchive
    $extracted = @(Export-OpenJadeBFEntry -Path $GameArchive -All -OutputDirectory (Join-Path $run 'real'))
    Assert ($extracted.Count -eq $real.Entries.Count) 'Real extraction count matches index'
    Assert ((Get-FileHash -LiteralPath $GameArchive).Hash -eq $before) 'Real archive is unchanged'
    # Check output bytes against source ranges without any prior extraction.
    $source = [IO.File]::OpenRead((Resolve-Path -LiteralPath $GameArchive).ProviderPath)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        for ($i = 0; $i -lt $real.Entries.Count; $i++) {
            $entry = $real.Entries[$i]
            $source.Position = $entry.AbsoluteDataStart
            $buffer = New-Object byte[] 65536
            $remaining = [long]$entry.DataLength
            $sha.Initialize()
            while ($remaining -gt 0) {
                $read = $source.Read($buffer,0,[int][Math]::Min($remaining,$buffer.Length))
                if ($read -eq 0) { throw 'Unexpected end of source range.' }
                [void]$sha.TransformBlock($buffer,0,$read,$buffer,0)
                $remaining -= $read
            }
            [void]$sha.TransformFinalBlock([byte[]]@(),0,0)
            $expected = [BitConverter]::ToString($sha.Hash).Replace('-','')
            Assert ($expected -eq $extracted[$i].SHA256) "Source range matches extraction: $($entry.FileName)"
        }
    }
    finally { $source.Dispose(); $sha.Dispose() }
    $realResult = [pscustomobject]@{ Path=$real.Path; SHA256=$before; Entries=$real.Entries.Count; SourceRangeMatches=$extracted.Count }
    $real.Entries | Export-Csv -LiteralPath (Join-Path $run 'index.csv') -NoTypeInformation -Encoding UTF8
    $extracted | Export-Csv -LiteralPath (Join-Path $run 'extraction.csv') -NoTypeInformation -Encoding UTF8
}
[pscustomobject]@{ Date=(Get-Date).ToString('o'); PowerShell=$PSVersionTable.PSVersion.ToString()
    Checks=$checks.Count; Passed=$checks.ToArray(); RealArchive=$realResult } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
if ($realResult) { $realResult | Format-List }
