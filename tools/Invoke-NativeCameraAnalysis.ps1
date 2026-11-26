#requires -Version 7.6
<#
.SYNOPSIS
    Imports a verified POP.EXE copy into a new local Ghidra project and exports camera entry-point evidence.
.DESCRIPTION
    Static analysis only. Decompiled game code stays in local reports and must not be published.
    Requires a portable Ghidra installation and a compatible full JDK.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Path,
    [Parameter(Mandatory)][string]$GhidraDirectory,
    [Parameter(Mandatory)][string]$JavaHome,
    [Parameter(Mandatory)][string]$OutputDirectory
)
Set-StrictMode -Version 3.0
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $Path).ProviderPath
$ghidra=(Resolve-Path -LiteralPath $GhidraDirectory).ProviderPath
$jdk=(Resolve-Path -LiteralPath $JavaHome).ProviderPath
if ($IsWindows) {
    $launcher = Join-Path $ghidra 'support/analyzeHeadless.bat'
    $javac = Join-Path $jdk 'bin/javac.exe'
} else {
    $launcher = Join-Path $ghidra 'support/analyzeHeadless'
    $javac = Join-Path $jdk 'bin/javac'
}
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf) -or -not (Test-Path -LiteralPath $javac -PathType Leaf)) { throw 'Ghidra launcher or full JDK is missing.' }
$expected='6587D499F4EA6D0895179F74487045BC2C82A9D4E08A0A5046C1FB88EE3B6EC9'
if((Get-FileHash -LiteralPath $source).Hash -ne $expected){throw 'Unsupported executable hash.'}
$separator = [IO.Path]::DirectorySeparatorChar
$root = [IO.Path]::TrimEndingDirectorySeparator([IO.Path]::GetFullPath($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)))
$game = [IO.Path]::GetFullPath((Join-Path (Split-Path $PSScriptRoot -Parent) 'game'))
if ($root.Equals($game, [StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game + $separator, [StringComparison]::OrdinalIgnoreCase)) { throw 'Game directory is read-only.'}
if(Test-Path -LiteralPath $root){throw 'Output directory must be new.'}
$ancestor=$root
while($ancestor){
    if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output contains a reparse point.'}
    $ancestor=[IO.Path]::GetDirectoryName($ancestor)
}
[void](New-Item -ItemType Directory -Path $root)
$snapshot=Join-Path $root 'POP.EXE'
Copy-Item -LiteralPath $source -Destination $snapshot
if((Get-FileHash $snapshot).Hash -ne $expected){throw 'Snapshot hash mismatch.'}
$oldJava=$env:JAVA_HOME
$oldHeap=$env:GHIDRA_HEADLESS_MAXMEM
$oldOptions=$env:GHIDRA_HEADLESS_JAVA_OPTIONS
try {
    $env:JAVA_HOME=$jdk
    $env:GHIDRA_HEADLESS_MAXMEM='2G'
    $env:GHIDRA_HEADLESS_JAVA_OPTIONS='-Djava.awt.headless=true'
    & $launcher $root CameraResearch -import $snapshot -analysisTimeoutPerFile 300 -max-cpu 2 -scriptPath (Join-Path $PSScriptRoot 'ghidra') -postScript OpenJadeCameraEntryPoints.java (Join-Path $root 'evidence') -log (Join-Path $root 'analysis.log') -scriptlog (Join-Path $root 'script.log')
    if($LASTEXITCODE -ne 0){throw 'Ghidra analysis failed.'}
    $evidence=Join-Path $root 'evidence/entry-points.txt'
    if(-not (Test-Path -LiteralPath $evidence)){throw 'Ghidra did not produce entry-point evidence; inspect the logs.'}
    if((Get-FileHash $source).Hash -ne $expected -or (Get-FileHash $snapshot).Hash -ne $expected){throw 'Executable hash changed.'}
    [pscustomobject]@{SourceSHA256=$expected;SnapshotSHA256=(Get-FileHash $snapshot).Hash;GhidraDirectory=$ghidra;JavaHome=$jdk;Evidence=$evidence;GameExecuted=$false} |
        ConvertTo-Json | Set-Content (Join-Path $root 'verification.json') -Encoding utf8NoBOM
    Get-Content -LiteralPath $evidence
} finally {
    $env:JAVA_HOME=$oldJava
    $env:GHIDRA_HEADLESS_MAXMEM=$oldHeap
    $env:GHIDRA_HEADLESS_JAVA_OPTIONS=$oldOptions
}