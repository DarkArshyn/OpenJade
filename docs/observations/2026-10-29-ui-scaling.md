# Native interface scaling — 2026-10-29

The preceding exporter reduced pop.dds from 1024x256 to 480x120 and
officialcursor_alpha2_desaturated.dds from 128x128 to 40x40. It selected only the
first prepared MFT font (36). All UI sampling used nearest filtering. Those
choices caused avoidable loss of source detail and visible enlargement steps.

## Changes

- OJUI0003 stores the logo and cursor at their decoded source dimensions. Byte
  comparisons against the DDS base-level RGBA pixels pass for both resources.
- The existing Read-MFT tool exports variants 10,12,14,16,18,20,22,24,26,28,36,48.
  The sprite package contains 1,140 glyph entries and eleven non-font entries.
- Text chooses the smallest variant at least equal to nominal label size times
  the existing 1.25 layout factor times actual viewport width / 800; selection
  caps at 48. Bearings/advances and scale come from the chosen font. Width limits
  and hit rectangles are computed from the resulting text, preserving interaction.
- The Vulkan UI sampler now uses linear min/mag filtering at base mip level.
  Scene filtering is unaffected. Glyph gutters use transparent white coverage.
- The 800x600 layout still displays the logo at 480x120 and cursor at 40x40.
  Texture dimensions and screen dimensions are separate; a larger source does
  not make a larger widget. Five 512x512 atlases plus the 1024x256 logo make six
  images, 44 total with the current scene. Python remains export-only.

## Checks

29 Rust tests pass; new coverage checks variant thresholds, largest-size fallback,
rectangular UI rows and malformed dimension rejection without scene mutation.
The local resource audit confirms original logo/cursor dimensions and byte-for-byte
decoded RGBA equality. The native Vulkan smoke traverses 800x600 -> 1600x1200 ->
800x600, settings pages and Camera02 with legacy-unorm: 80 frames, zero validation
errors. Interactive inspection at 1600x1200 checked main menu, Options, text,
logo, cursor and click targets; 15,573 frames, zero validation errors on exit.

Local evidence: reports/engine-ui-scale-20261029 and reports/native-ui-fonts-20261029.
No original game resources were modified or added to source control.

## Limits

This is an OpenJade sampling/selection policy; the original game's font selection
is unknown. Original MFT bearing/layout semantics remain a research interpretation.
Sizes beyond the largest source glyph still require enlargement; this is not a
vector font. UI mipmaps and restoration of every other DDS widget's dimensions
are outside this change. Linear filtering can soften small text. The user's
preference for legacy-unorm is useful visual evidence, not a proof of original
color state; the default color pipeline is unchanged.
