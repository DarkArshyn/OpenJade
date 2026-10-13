#requires -Version 5.1
<#
.SYNOPSIS
    Builds an optional local test oracle from verified official miniLZO 2.10 sources.
.DESCRIPTION
    Requires an existing MSVC x64 compiler. Does not download or install tools.
    The freestanding build uses local minimal headers, without the Windows SDK
    or C runtime. The official miniLZO files are not modified or redistributed.
#>
[CmdletBinding()]
param([Parameter(Mandatory)][string]$MiniLzoDirectory,
    [Parameter(Mandatory)][string]$CompilerPath,[Parameter(Mandatory)][string]$OutputDirectory)
$ErrorActionPreference='Stop'
$source=(Resolve-Path -LiteralPath $MiniLzoDirectory).ProviderPath
$compiler=(Resolve-Path -LiteralPath $CompilerPath).ProviderPath
$hashes=@{
    'minilzo.c'='489430D9A4290082DC5C2B90BB67822586F985A12353E3A1368E633FA4136DD6'
    'minilzo.h'='7A534954BF04E611CD79905EDE932C41A2907AF461BA532A0F2D2C08463070EE'
    'lzoconf.h'='63BF0574A0DF2FA703060282CC5CFA60D86E73D11B1A5F2FAF261FFE6809F99D'
    'lzodefs.h'='7CDC24F7D8762F0908B30F4959442798427AF8C01C6D925F5594114A45A2A89E'
}
foreach($name in $hashes.Keys){if((Get-FileHash (Join-Path $source $name)).Hash -cne $hashes[$name]){throw "Reference source mismatch: $name"}}
$root=$ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputDirectory)
$game=Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) 'game'
if($root.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or $root.StartsWith($game+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'The game directory is read-only.'}
if(Test-Path $root){throw 'Reference output directory already exists.'}
$ancestor=$root
while($ancestor){
    if((Test-Path -LiteralPath $ancestor) -and ((Get-Item -LiteralPath $ancestor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Output path contains a reparse point.'}
    $ancestor=[IO.Path]::GetDirectoryName($ancestor)
}
[void][IO.Directory]::CreateDirectory($root)
Push-Location $root
try {
    & $compiler /nologo /Od /GS- /LD /DLZO_CFG_FREESTANDING=1 /DLZO_BITOPS_USE_MSC_BITSCAN=0 /I (Join-Path $PSScriptRoot 'headers') /I $source (Join-Path $PSScriptRoot 'oracle.c') (Join-Path $source 'minilzo.c') /link /NODEFAULTLIB /NOENTRY /MACHINE:X64 /OUT:oracle.dll
    if($LASTEXITCODE -ne 0){throw 'Reference compilation failed.'}
    [pscustomobject]@{MiniLzoVersion='2.10';SourceHashes=$hashes;Compiler=$compiler;CompilerSHA256=(Get-FileHash $compiler).Hash
        OracleSHA256=(Get-FileHash (Join-Path $root 'oracle.dll')).Hash;Freestanding=$true} | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $root 'build.json') -Encoding UTF8
    Write-Host "Reference DLL: $(Join-Path $root 'oracle.dll')"
}finally{Pop-Location}
