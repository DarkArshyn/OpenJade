#requires -Version 5.1
<# .SYNOPSIS
Creates a static 800x600 logo/text prototype and a bounded style comparison.
.DESCRIPTION
Requires Python with Pillow and NumPy. Game backgrounds and behavior are absent.
The unmodified bilinear model remains the main prototype; fitted style is separate.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$AssetRoot,[Parameter(Mandatory)][string]$ReferenceImage,
      [Parameter(Mandatory)][string]$OutputDirectory,[Parameter(Mandatory)][string]$PythonPath)
$ErrorActionPreference='Stop'
& (Join-Path $PSScriptRoot 'Compare-MFTMenu.ps1') -AssetRoot $AssetRoot -ReferenceImage $ReferenceImage -OutputDirectory $OutputDirectory -PythonPath $PythonPath
$root=(Resolve-Path -LiteralPath $OutputDirectory).ProviderPath
& (Join-Path $PSScriptRoot 'Export-DDSPreview.ps1') -Path (Join-Path $AssetRoot 'texture/pop.dds') -OutputDirectory (Join-Path $root 'logo') | Out-Null
$settings=New-Object Xml.XmlReaderSettings
$settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit
$reader=[Xml.XmlReader]::Create((Join-Path $AssetRoot 'pop4mainmenu.mgm'),$settings)
try{$doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null;$doc.Load($reader)}finally{$reader.Dispose()}
$logo=$doc.SelectSingleNode('//PAGE[NAME="P_MainMenu"]/CHILDREN/IMAGE[NAME="Logo"]')
if($logo.MATERIAL -ne 'POP'){throw 'Unsupported logo material.'}
$frame=$logo.SelectSingleNode('KEYFRAMES/KEYFRAME[IDX="0"]')
[pscustomobject]@{Left=[int]$frame.LEFT;Top=[int]$frame.TOP;Right=[int]$frame.RIGHT;Bottom=[int]$frame.BOTTOM} |
    ConvertTo-Json | Set-Content (Join-Path $root 'logo-geometry.json') -Encoding UTF8
& $PythonPath (Join-Path $PSScriptRoot '../src/menu_style_experiment.py') $root
if($LASTEXITCODE -ne 0){throw 'Style experiment failed.'}
Write-Host "Static prototype: $root"
