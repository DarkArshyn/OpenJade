#requires -Version 5.1
Set-StrictMode -Version Latest

function Read-OpenJadeMFT {
    <# .SYNOPSIS
    Reads the observed PC GOG fixed-record MFT layout without modifying input.
    Metric names are deliberately neutral where their semantics are unverified.
    #>
    [CmdletBinding()]
    param([Parameter(Mandatory)][byte[]]$Bytes)
    if($Bytes.Length -lt 5248){throw 'Truncated MFT header or glyph table.'}
    if([Text.Encoding]::ASCII.GetString($Bytes,0,11) -cne "Magma Font`0"){throw 'Invalid MFT signature.'}
    if([BitConverter]::ToUInt32($Bytes,11) -ne 110){throw 'Unsupported MFT header word.'}
    $width=[int][BitConverter]::ToUInt16($Bytes,5244)
    $height=[int][BitConverter]::ToUInt16($Bytes,5246)
    if($width -lt 1 -or $height -lt 1 -or $width -gt 4096 -or $height -gt 4096){throw 'Unsupported atlas dimensions.'}
    if($Bytes.Length -ne 5248+$width*$height){throw 'Atlas length mismatch or unsupported trailing data.'}
    $nameLength=0
    while($nameLength -lt 64 -and $Bytes[15+$nameLength] -ne 0){$nameLength++}
    if($nameLength -eq 64){throw 'Unterminated font name.'}
    $glyphs=@(for($i=0;$i -lt 224;$i++){
        $offset=84+$i*23
        $code=[BitConverter]::ToUInt16($Bytes,$offset)
        if($code -ne 32+$i){throw 'Unsupported glyph code sequence.'}
        $uv=@(for($j=0;$j -lt 4;$j++){
            $value=[BitConverter]::ToSingle($Bytes,$offset+7+$j*4)
            if([Single]::IsNaN($value) -or [Single]::IsInfinity($value) -or $value -lt 0 -or $value -gt 1){throw 'Invalid glyph UV.'}
            $value
        })
        $positions=@(($uv[0]*$width-0.5),($uv[1]*$height-0.5),($uv[2]*$width-0.5),($uv[3]*$height-0.5))
        foreach($p in $positions){if([Math]::Abs($p-[Math]::Round($p)) -gt 0.0001){throw 'Unsupported non-half-texel UV.'}}
        $x=[int][Math]::Round($positions[0]);$y=[int][Math]::Round($positions[1])
        $right=[int][Math]::Round($positions[2]);$bottom=[int][Math]::Round($positions[3])
        if($x -lt 0 -or $y -lt 0 -or $right -ge $width -or $bottom -ge $height -or $right-$x -ne $Bytes[$offset+2]+1 -or $bottom-$y -ne $Bytes[$offset+3]+1){throw 'Unsupported glyph rectangle.'}
        [pscustomobject]@{Code=$code;Offset=$offset;EndOffset=$offset+23;Width=$Bytes[$offset+2];Height=$Bytes[$offset+3]
            Metric2Raw=$Bytes[$offset+4];Metric3Raw=$Bytes[$offset+5];Metric4Raw=$Bytes[$offset+6]
            U0=$uv[0];V0=$uv[1];U1=$uv[2];V1=$uv[3];AtlasX=$x;AtlasY=$y;AtlasRight=$right;AtlasBottom=$bottom}
    })
    $pixels=New-Object byte[] ($width*$height)
    [Array]::Copy($Bytes,5248,$pixels,0,$pixels.Length)
    [pscustomobject]@{Name=[Text.Encoding]::ASCII.GetString($Bytes,15,$nameLength);HeaderWord=110
        SizeWord=[BitConverter]::ToUInt32($Bytes,79);UnknownByte83=$Bytes[83]
        UnknownTailHex=[BitConverter]::ToString($Bytes,5236,8)
        Width=$width;Height=$height;PixelOffset=5248;Glyphs=$glyphs;Pixels=$pixels}
}
Export-ModuleMember -Function Read-OpenJadeMFT
