# Native texture dimensions and filtering — 2026-10-28

Scope: the existing 46-object PC GOG menu export only. Game data is read-only.

## Change and evidence

- Previous exporter enlarged every texture to 512x512 with nearest resampling.
  GPU images contained one mip level. Ordinary materials used nearest filtering;
  supported fog/fixture materials used linear filtering.
- OJSCN003 preserves the 38 base images at their decoded sizes, 32x32 through
  256x256, including rectangular dimensions. Pixel-by-pixel comparison of the
  package against the 38 PNG inputs passed. Transport padding is not sampled.
- GPU images now use individual native dimensions. Ordinary-material filtering
  can be nearest or linear at level zero. Optional trilinear filtering generates
  mipmaps for scene images, including fog/fixtures. UI stays nearest/base-level.
- Generated mipmaps use linear Vulkan blits in R8G8B8A8_SRGB after a format-feature
  check. No anisotropy, LOD bias or alpha-coverage preservation is applied.
  The color-space assumptions remain diagnostic and were not changed here.

## Original lower-level data audit

The source hash is checked against the existing scene report. Duplicate numeric
keys include non-image records: selection follows the existing bounded image
decoder, requiring one supported image payload per key. The 38 exported images
include repeated use of some resources; counts below are image uses, not unique IDs.

- 21 BC3 image uses: payload extents fit successive lower-resolution blocks with
  no leftover bytes. This is an extent check, not proof of runtime mip selection.
- 15 BC1 image uses: successive block extents leave four bytes after the candidate
  chain. The tail is not interpreted here.
- One raw image use has a complete five-level extent under the existing decoder.
- Raw fixture texture `6600D792` retains an unresolved lower-level layout. A
  naive full-chain calculation leaves 84 bytes; that arithmetic does not identify
  their semantics and is not a replacement decoder.

PNG inputs carry only base images. Original mipmaps are therefore **not imported**;
the generated chains are explicitly diagnostic. Original filtering, LOD selection
and cutout coverage need separate evidence before claiming fidelity.

## Validation

- 14 Rust tests: existing package/navigation cases plus v3 bounds, truncation and
  exact native-row extraction.
- 3 material-export tests, including non-square distinct pixels and padding.
- `cargo fmt --all --check` and Clippy with warnings denied.
- Nearest, linear and trilinear: each 80-frame Vulkan smoke with two resizes and
  accelerated Camera02 playback, zero validation errors on GPU.
- Checker and old OJSCN001 package regression: each 80 frames, zero errors.
- Interactive trilinear preview: 11,058 frames, zero validation errors; menu
  overlay and quit confirmation inspected. This is not a pixel-parity test.

Local evidence: `reports/engine-textures-20261028/menu.ojscene`, `manifest.json`,
`texture-audit.json`, `trilinear.png`. Source export:
`reports/menu-fixture-materials-20261025/renders/horizontal-angle`.
The native menu still differs in fog, lighting and material/color behavior;
filtering alone does not resolve those differences.

