#requires -Version 5.1
<#
.SYNOPSIS
    Checks text DAT/INI byte preservation and input/output validation.
.PARAMETER TextDat
    Optional local Windows-1252 text DAT to round-trip without modifying it.
.EXAMPLE
    .\tests\Test-TextDat.ps1
#>
[CmdletBinding()]
param([string]$TextDat)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$project = Split-Path $PSScriptRoot -Parent
$run = Join-Path $project ('reports/textdat-' + [guid]::NewGuid().ToString('N'))
[void][IO.Directory]::CreateDirectory($run)
$checks = New-Object 'System.Collections.Generic.List[string]'
function Assert([bool]$Condition,[string]$Name) {
    if (-not $Condition) { throw "FAIL: $Name" }
    $checks.Add($Name)
}
function Assert-Throws([scriptblock]$Action,[string]$Name) {
    $failed = $false
    try { & $Action | Out-Null } catch { $failed = $true }
    Assert $failed $Name
}
$toIni = Join-Path $project 'tools/Convert-DatToIni.ps1'
$toDat = Join-Path $project 'tools/Convert-IniToDat.ps1'
$cp = [Text.Encoding]::GetEncoding(1252)
$fixture = Join-Path $run 'fixture.dat'
$cases = @('', "[Section]`r`n;comment`r`nKey = value||{0}%02u`r`n", "[Section]`nKey=value", ('Accents=' + [char]233 + [char]8364 + [char]339))
foreach ($case in $cases) {
    [IO.File]::WriteAllBytes($fixture,$cp.GetBytes($case))
    $before = (Get-FileHash $fixture).Hash
    $stem = [guid]::NewGuid().ToString('N')
    $ini = Join-Path $run ($stem + '.ini')
    $dat = Join-Path $run ($stem + '.dat')
    & $toIni -Path $fixture -Output $ini | Out-Null
    & $toDat -Path $ini -Output $dat | Out-Null
    Assert ((Get-FileHash $ini).Hash -eq $before) 'DAT to INI preserves exact bytes'
    Assert ((Get-FileHash $dat).Hash -eq $before) 'INI to DAT preserves exact bytes'
    Assert ((Get-FileHash $fixture).Hash -eq $before) 'Source remains unchanged'
}
Assert-Throws { & $toIni -Path $fixture -Output $fixture } 'Same-path output is refused'
Assert-Throws { & $toIni -Path $fixture -Output $ini } 'Existing output is refused'
Assert-Throws { & $toIni -Path $fixture -Output (Join-Path $project 'game/forbidden.ini') } 'Game output is refused'
foreach ($invalid in @([byte[]](65,0,66),[byte[]](239,187,191,65),[byte[]](255,254,65),[byte[]](254,255,65))) {
    [IO.File]::WriteAllBytes($fixture,$invalid)
    $output = Join-Path $run ([guid]::NewGuid().ToString('N') + '.ini')
    Assert-Throws { & $toIni -Path $fixture -Output $output } 'Binary NUL or Unicode BOM is refused'
    Assert (-not (Test-Path $output)) 'Rejected input creates no output'
}
$real = $null
if ($TextDat) {
    $before = (Get-FileHash -LiteralPath $TextDat).Hash
    $ini = Join-Path $run 'real.ini'
    $dat = Join-Path $run 'real.dat'
    & $toIni -Path $TextDat -Output $ini | Out-Null
    & $toDat -Path $ini -Output $dat | Out-Null
    Assert ((Get-FileHash $ini).Hash -eq $before) 'Real INI bytes match source'
    Assert ((Get-FileHash $dat).Hash -eq $before) 'Real DAT round-trip bytes match source'
    Assert ((Get-FileHash -LiteralPath $TextDat).Hash -eq $before) 'Real source remains unchanged'
    $real = [pscustomobject]@{ FileName=[IO.Path]::GetFileName($TextDat); SHA256=$before; Length=(Get-Item -LiteralPath $TextDat).Length }
}
[pscustomobject]@{ Date=(Get-Date).ToString('o'); PowerShell=$PSVersionTable.PSVersion.ToString()
    Checks=$checks.Count; Passed=$checks.ToArray(); RealTextDat=$real } |
    ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $run 'verification.json') -Encoding UTF8
Write-Host "PASS: $($checks.Count) checks. Results: $run"
if ($real) { $real | Format-List }
