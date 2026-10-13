# Legacy DDS texture preview

Date: 2026-10-13. Scope: the single-level DXT1 and DXT5 DDS files observed in
the PC GOG POPData menu texture directory.

## References

Microsoft documentation, consulted 2026-10-13:

- [DDS_HEADER](https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-header)
  defines the 124-byte header, dimensions, mip count and surface flags.
- [DDS_PIXELFORMAT](https://learn.microsoft.com/en-us/windows/win32/direct3ddds/dds-pixelformat)
  defines the 32-byte pixel-format record and FourCC flag.
- [Block Compression](https://learn.microsoft.com/en-us/windows/win32/direct3d10/d3d10-graphics-programming-guide-resources-block-compression)
  describes BC1/DXT1 and BC3/DXT5 block layouts and interpolation.

The implementation is original OpenJade C#, compiled by Windows PowerShell 5.1
with Add-Type. It uses System.Drawing to save PNGs. No game engine code or
external image package is needed for normal use. Optional tests compare pixels
with Pillow's independent DDS decoder.

## Supported input

The file must have `DDS` magic, a 124-byte main header and a 32-byte pixel
format record. FourCC must be DXT1 or DXT5 with its flag set. Only a single 2D
surface is supported: depth and Caps2 must be zero, and mip count zero or one.
DX10, cubemaps, volumes, mip chains and other pixel formats are refused.

Data begins at absolute file offset 128. Blocks cover 4 by 4 pixels and occupy
8 bytes for DXT1 or 16 for DXT5. The exact input size must match the rounded-up
block count; truncated data and extra bytes are refused. Partial edge blocks
are decoded and cropped to the declared width and height.

Dimensions must be 1 through 8,192, with at most 16,777,216 pixels in total.
The command caps the source file at 64 MiB before loading it. Allocation limits
are checked before pixel buffers are created.

RGBBitCount is preserved as a raw header value but is not used for FourCC
textures. Several observed DXT5 files contain 512 there; treating this as a
pixel stride would be incorrect. LinearSize and header flags are retained;
block counts are calculated from dimensions and FourCC.

## Decoding and output

DXT1 supports both four-color and three-color/transparent modes. DXT5 always
uses the four-color palette plus its independent alpha palette. RGB565
endpoints expand through bit replication; interpolation uses integer division.
Pixel order is top-to-bottom RGBA, without flips, color correction, scaling or
game material processing. This is a texture inspection tool, not a renderer.

`tools/Export-DDSPreview.ps1 -Path INPUT -OutputDirectory NEW_DIRECTORY` writes:

| File | Purpose |
| --- | --- |
| source.dds | Exact input bytes, verified by SHA-256 |
| texture.png | Original dimensions and decoded transparency |
| preview.png | Same dimensions, composited over a 16-pixel dark checkerboard |
| texture.json | Source path/hash, raw header fields, dimensions and RGBA/PNG hashes |

The checkerboard is solely for inspecting alpha; it is not part of the texture.
Its composite is performed on byte values without a color-space conversion.
PNG hashes are encoded-file hashes; RgbaSHA256 identifies the decoded pixels.

The source stays open read-only, denying writes/deletion during conversion.
The destination must be new, outside game, with no reparse-point ancestor.
Validation completes before output creation. I/O failure can leave partial
outputs; retry in a new directory. Generated images remain under local reports.

## Tests

```powershell
.\tests\Test-DDSPreview.ps1
.\tests\Test-DDSPreview.ps1 -TextureDirectory .\reports\POPData-extracted\menu\texture
# Optional independent reference, using an existing Python with Pillow:
.\tests\Test-DDSPreview.ps1 -TextureDirectory .\reports\POPData-extracted\menu\texture -PythonPath 'C:\path\to\python.exe'
```

The reference test compares every RGBA byte from Pillow's DDS reader with
the exported PNG and checks that PNG encoding preserves the decoder's RGBA
hash. Neither Pillow nor Python is installed by these scripts. Restart the
PowerShell process after editing the C# source to avoid reusing a loaded type.
