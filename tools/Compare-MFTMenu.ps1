#requires -Version 5.1
<# .SYNOPSIS
Builds six experimental main-menu labels and compares them with an 800x600 capture.
.DESCRIPTION
Uses PowerShell for the existing MFT renderer and Python (Pillow, NumPy) for
resampling and image measurements. This is a bounded research experiment.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$AssetRoot,
      [Parameter(Mandatory)][string]$ReferenceImage,
      [Parameter(Mandatory)][string]$OutputDirectory,
      [Parameter(Mandatory)][string]$PythonPath)
$ErrorActionPreference='Stop'
$root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
$game=Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
if($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'The game directory is read-only.'}
if(Test-Path -LiteralPath $root){throw 'Output directory already exists.'}
$ancestor=$root
while($ancestor){
    if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output path contains a reparse point.'}
    $ancestor=[IO.Path]::GetDirectoryName($ancestor)
}
function Read-ResearchXml($path){
    # These two observed MGM files are XML-compatible. Other MGM layouts are unsupported.
    $settings=New-Object Xml.XmlReaderSettings
    $settings.DtdProcessing=[Xml.DtdProcessing]::Prohibit
    $reader=[Xml.XmlReader]::Create($path,$settings)
    try{$doc=New-Object Xml.XmlDocument;$doc.XmlResolver=$null;$doc.Load($reader);return ,$doc}finally{$reader.Dispose()}
}
$mainPath=Join-Path $AssetRoot 'pop4mainmenu.mgm'
$commonPath=Join-Path $AssetRoot 'pop4common.mgm'
$main=Read-ResearchXml $mainPath;$common=Read-ResearchXml $commonPath
if($main.PACKAGE.PAGESIZE -ne '640 480'){throw 'Unsupported page size.'}
$page=$main.SelectSingleNode('//PAGE[NAME="P_MainMenu"]')
$reference=(Resolve-Path -LiteralPath $ReferenceImage).ProviderPath
$rows=@();$inputs=@($mainPath,$commonPath,$reference)
foreach($name in @('NewGame','LoadGame','Options','Credits','Quit','Back')){
    $button=$page.SelectSingleNode('CHILDREN/BUTTONINST[NAME="'+$name+'"]')
    $area=[string]$button.LINK.AREA
    $caption=$common.SelectSingleNode('//BUTTON[NAME="'+$area+'"]/CHILDREN/TEXT[NAME="Caption"]')
    if(-not $caption -or $button.LINK.PACKAGE -ne 'POP4Common'){throw 'Unsupported caption link.'}
    $frame=$caption.SelectSingleNode('KEYFRAMES/KEYFRAME[IDX="0"]')
    $fontPath=Join-Path $AssetRoot ('fonts/'+$caption.FONT+'.mft')
    $fontPath=(Resolve-Path -LiteralPath $fontPath).ProviderPath
    $inputs+=$fontPath
    $position=([string]$button.KEYFRAMES.KEYFRAME.POSITION).Split(' ')
    $spec=& (Join-Path $PSScriptRoot 'Export-MFTTextPreview.ps1') -Path $fontPath -OutputDirectory (Join-Path $root $name) -Text ([string]$button.LABEL)
    $rows+=[pscustomobject]@{Name=$name;Text=[string]$button.LABEL;X=[double]$position[0];Y=[double]$position[1]
        Height=[double]::Parse($frame.HEIGHT,[Globalization.CultureInfo]::InvariantCulture)
        Left=[double]$frame.LEFT;Top=[double]$frame.TOP;Color=[string]$frame.COLOR;Bold=[string]$caption.BOLD
        Font=[string]$caption.FONT;FontSizeWord=36;Specimen=$spec}
    if($caption.FONT -ne 'Atlantis MF Regular 36'){throw 'Unsupported font for this experiment.'}
}
$hashes=@($inputs | Select-Object -Unique | ForEach-Object {[pscustomobject]@{Path=$_;SHA256=(Get-FileHash -LiteralPath $_).Hash}})
[pscustomobject]@{Rows=$rows;Inputs=$hashes;ReferenceImage=$reference;PageWidth=640;PageHeight=480;GameRenderingValidated=$false} |
    ConvertTo-Json -Depth 8 | Set-Content (Join-Path $root 'experiment.json') -Encoding UTF8
& $PythonPath (Join-Path $PSScriptRoot '../src/compare_mft_menu.py') $root
if($LASTEXITCODE -ne 0){throw 'Image comparison failed.'}
foreach($inputFile in $hashes){if((Get-FileHash -LiteralPath $inputFile.Path).Hash -cne $inputFile.SHA256){throw 'Input changed during comparison.'}}
Write-Host "Menu comparison: $root"
