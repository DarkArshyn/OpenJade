#requires -Version 5.1
<# .SYNOPSIS
Opens the experimental menu viewer from an existing prototype report.
.DESCRIPTION
Requires Python with tkinter and Pillow. Controls simulate selection and actions;
no game process is started and input resources remain read-only.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$ReportDirectory,
      [Parameter(Mandatory)][string]$PythonPath,[switch]$SmokeTest)
$ErrorActionPreference='Stop'
$report=(Resolve-Path -LiteralPath $ReportDirectory).ProviderPath
$arguments=@((Join-Path $PSScriptRoot '../src/menu_viewer.py'),$report)
if($SmokeTest){$arguments+='--smoke-test'}
& $PythonPath @arguments
if($LASTEXITCODE -ne 0){throw 'Menu viewer failed.'}
