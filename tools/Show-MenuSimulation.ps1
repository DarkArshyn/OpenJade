#requires -Version 7.6
<# .SYNOPSIS
Runs the single-window menu simulation with session-only settings.
.DESCRIPTION
Uses existing exported assets. Does not modify game settings or profiles.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$ReportDirectory,
      [Parameter(Mandatory)][string]$PythonPath,[switch]$SmokeTest)
Set-StrictMode -Version 3.0
$ErrorActionPreference='Stop'
$report=(Resolve-Path -LiteralPath $ReportDirectory).ProviderPath
$arguments=@((Join-Path $PSScriptRoot '../src/menu_simulation.py'),$report)
if($SmokeTest){$arguments+='--smoke-test'}
& $PythonPath @arguments
if($LASTEXITCODE -ne 0){throw 'Menu simulation failed.'}