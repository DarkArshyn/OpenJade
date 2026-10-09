#requires -Version 5.1
Set-StrictMode -Version Latest

function Convert-OpenJadeTextDat {
    <#
    .SYNOPSIS
        Copies Windows-1252 text between DAT and INI filenames without changing bytes.
    .DESCRIPTION
        Does not interpret properties or decode binary DAT formats. Validates a
        reversible Windows-1252 representation, rejects NUL bytes and Unicode
        BOMs, and preserves whitespace, line endings and the final newline.
        UTF-8 without a BOM cannot be reliably distinguished from Windows-1252.
    .PARAMETER Path
        Source file saved as Windows-1252 without a BOM.
    .PARAMETER Output
        New output filename. Existing files and game-directory writes are refused.
    .EXAMPLE
        Convert-OpenJadeTextDat -Path .\reports\pop4pclocal.dat -Output .\reports\pop4pclocal.ini
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Output)
    $source = (Resolve-Path -LiteralPath $Path -ErrorAction Stop).ProviderPath
    $destination = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Output)
    $game = Join-Path (Split-Path $PSScriptRoot -Parent) 'game'
    if ($destination.Equals($game,[StringComparison]::OrdinalIgnoreCase) -or
        $destination.StartsWith($game + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'The game directory is read-only.' }
    if (Test-Path -LiteralPath $destination) { throw "Output already exists: $destination" }
    # Reject output ancestors that redirect writes, including junctions.
    $ancestor = [IO.Path]::GetDirectoryName($destination)
    while ($ancestor) {
        if (Test-Path -LiteralPath $ancestor) {
            $item = Get-Item -LiteralPath $ancestor -Force -ErrorAction Stop
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Output path contains a reparse point.' }
        }
        $ancestor = [IO.Path]::GetDirectoryName($ancestor)
    }
    $bytes = [IO.File]::ReadAllBytes($source)
    if ($bytes -contains [byte]0) { throw 'NUL bytes are not supported by this text-only converter.' }
    if (($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) -or
        ($bytes.Length -ge 2 -and (($bytes[0] -eq 255 -and $bytes[1] -eq 254) -or ($bytes[0] -eq 254 -and $bytes[1] -eq 255)))) {
        throw 'Unicode BOM detected. Save the input as Windows-1252 without a BOM.'
    }
    $encoding = [Text.Encoding]::GetEncoding(1252,[Text.EncoderFallback]::ExceptionFallback,[Text.DecoderFallback]::ExceptionFallback)
    $text = $encoding.GetString($bytes)
    $encoded = $encoding.GetBytes($text)
    if ([Convert]::ToBase64String($encoded) -cne [Convert]::ToBase64String($bytes)) { throw 'Input is not reversible as Windows-1252.' }
    # Require an existing parent: callers choose where outputs are stored.
    $stream = [IO.File]::Open($destination,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $stream.Write($encoded,0,$encoded.Length) }
    finally { $stream.Dispose() }
    [pscustomobject]@{ InputPath=$source; OutputPath=$destination; Encoding='Windows-1252'
        Length=$encoded.Length; SHA256=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash }
}

Export-ModuleMember -Function Convert-OpenJadeTextDat
