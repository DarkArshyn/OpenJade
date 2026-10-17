# Menu3D texture candidates — 2026-10-16

Only the two payloads linked from the candidate ground/fog materials were
examined in the existing decoded scene. No additional archive extraction.

| Key | Record start | Payload bytes | Candidate dimensions | Candidate codec | Top-level bytes from payload +56 |
| --- | --- | --- | --- | --- | --- |
| 0x30000C67 | 3934184 | 736 | 32x32 | DXT1/BC1 | 512 |
| 0x30000C66 | 3923172 | 11000 | 128x64 | DXT5/BC3 | 8192 |

The dimensions occur twice: uint16 width/height at +12 and uint32 width/height
at +44/+48. The codecs are tested interpretations, not a decoded container enum.
Synthetic single-level DDS headers wrap the candidate bytes; these are not
original DDS files recovered verbatim. The remaining 168 and 2752 bytes are
preserved and not silently labelled or discarded as mipmaps.

Pillow's BC1/BC3 decoding and the independent OpenJade C# DXT1/DXT5 decoder
produce exactly identical RGBA bytes for both wrapped candidates. This validates
the block-decoding agreement, not the chosen container interpretation.

The 128x64 candidate has white RGB throughout and alpha 0..112, with 7413 of
8192 pixels nontransparent. Its preview resembles soft cloudy fog. This visually
supports, but does not prove, the zero-based material-selection hypothesis for
Menu3D_fake_fog. The 32x32 BC1 interpretation is entirely transparent black.
Thus the ground object is not yet established as the visible ground surface;
codec mode, render-state handling and the material hypothesis remain relevant.

No textured scene or verified UV projection is claimed. A faithful menu still
needs additional mesh layouts, material/render states, UV conventions, transforms
and the active camera. A small static assembly is a nearer milestone than the
complete animated menu.

`export_menu3d_texture_candidates.py` reproduces these exact-sample wrappers and
PNGs, preserving full payloads, tails and provenance. It rejects other input
hashes and existing output directories. The original `Export-DDSPreview.ps1`
validation must run under Windows PowerShell 5.1, not PowerShell 7.

Reports: `reports/menu3d-texture-candidates` holds previews and independent DDS
verification manifests; `reports/menu3d-texture-export` holds reproducible full
payload captures and `candidates.json`. All are excluded from Git.
