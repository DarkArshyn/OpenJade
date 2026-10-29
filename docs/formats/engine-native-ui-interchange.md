# OJUI0002 — native menu sprite bundle

OpenJade-only interchange, not an original Jade format. All integers/floats are
little-endian u32/f32. The reader requires a 512x512-slot scene and limits input
to 32 MiB. See [implementation evidence](../observations/2026-10-28-native-menus.md).

1. Eight ASCII bytes `OJUI0002`.
2. Atlas count (1..16), original MFT size word as f32 (1..256), entry count (100..256).
3. Each entry: name byte count (1..32), UTF-8 name, atlas index, x, y, width, height
   as five u32 values; glyph bearing x/y and advance as three f32 values.
4. Atlas pixels: atlas count * 512 * 512 * 4 bytes, straight-alpha RGBA.
5. Camera sample count (541), then 541 * 13 f32 values: position, right, up,
   forward, vertical FOV. These reuse the preceding Camera02 research export.

Required names: `c32` through `c126`, `panel`, `logo`, `cursor`, `eax`, `field`,
`up`, `down`, `bar`, `minus`, `plus`, `handle`. Atlas entries have two transparent
texels of packing separation. Names must be unique; rectangles must fit their
atlas. Floats must be finite; camera axes must be unit length, FOV bounded, and
the first sample must match the loaded scene. No trailing bytes are accepted.
Validation completes before appending pixels/dimensions to the scene.

Runtime quads use the existing nine-float vertex layout and are capped at 65,536
vertices by the renderer. UI draw order is preserved. Current samplers use linear/base
level independently of scene filtering (nearest before 2026-10-29). The current runtime uses only ASCII
glyphs; this does not establish general MFT character encoding or font semantics.

## OJMNU001 — independent local menu preferences

ASCII text, at most 8 KiB: magic line `OJMNU001`, twenty space-separated bounded
setting indexes, profile count, active index or `-`, profile names, thirty-six
keyboard labels, eighteen gamepad labels. Every field occupies its own line
except the setting indexes. Profiles are unique case-insensitively, trimmed,
1..20 printable ASCII characters; binding labels can be empty and are at most
20 characters. No extra lines are accepted. Profiles do not contain game state.

## OJUI0003 — native dimensions and multiple font variants

The magic is OJUI0003. After the existing atlas count, base font size and entry
count, add one u32 width/height pair per image, followed by a u32 font-count and
that many strictly increasing u32 sizes (1..128, at most sixteen). Entry count is
bounded to 2,048. The sprite entries and Camera02 tail retain their earlier layout.
Glyph names are now `f<size>_c<code>` for ASCII 32..126 for every listed font size.
All widget names remain required. No pixels are mutated during loading.

Each image occupies a fixed 512*512*4 transport slot. Its packed RGBA rows use the
declared width; unused slot bytes are padding. Dimensions must be nonzero and at
most 2048 each, with area no larger than 512*512. Thus the 1024x256 logo occupies
one slot without resampling. Scene images still use the scene's transport row
stride; UI images use their declared width. UV normalization uses each image's
dimensions. OJUI0002 defaults to 512x512 images and its single font as before.

The current export has 1,151 entries in six images (five 512x512 atlases and one
1024x256 logo). Glyph gutters are transparent white to avoid dark interpolation
fringes. Variant selection uses the actual 4:3 viewport scale and is an OpenJade
policy, not evidence of the original game's selection algorithm.
