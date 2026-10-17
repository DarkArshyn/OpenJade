#requires -Version 5.1
<# .SYNOPSIS
Builds five experimental resource-based menu pages for the existing viewer.
.DESCRIPTION
Requires Python with Pillow. Screenshot-derived text overrides are recorded in
catalog.json. Output must be new; input game resources remain read-only.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$AssetRoot,
      [Parameter(Mandatory)][string]$OutputDirectory,
      [Parameter(Mandatory)][string]$PythonPath)
$ErrorActionPreference='Stop'
& $PythonPath (Join-Path $PSScriptRoot '../src/build_menu_pages.py') $AssetRoot $OutputDirectory
if($LASTEXITCODE -ne 0){throw 'Menu page generation failed.'}
