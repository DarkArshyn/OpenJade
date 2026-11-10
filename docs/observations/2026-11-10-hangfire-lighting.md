# Hangfire modifier chain and menu lighting receivers

Date: 2026-11-10

## Scope and evidence

Read-only analysis of the frozen Menu3D resource and bounded observations of the local GOG research copy. No original game resources or executable code are included in the repository.

- Menu SHA-256: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
- GOG executable SHA-256: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
- Local captures: `hangfire-light` (draws and color preparation), `hangfire-chain` (modifier outputs), `hangfire-weights2` (modifier outputs and native weights).
- The first weight probe used an incorrect pointer and terminated the research process. Its empty output is excluded. The corrected probe completed; the research proxy was restored afterward.

## Remaining fixture deformation

`Menu3D_hangfire2.gao` (`30000D53`) and `Menu3D_hangfire1.gao` (`30000F45`) share mesh `2E004CC0`, with 49 vertices and groups of 56, 2 and 2 triangles. Both contain **two** type-1/version-25 modifiers, at payload offsets 435 and 471. Reading only the final modifier misses their composition.

| Order | Flags | Initial phase | Amplitude | Spatial factor | Rate factor | Group selector |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 21 | 0 | -0.0599999987 | -11.2835760 | -0.0299999993 | 0 |
| 2 | 4 | 0 | -0.0500000007 | -4.80000019 | 0.0399999991 | 0 |

The group selector resolves to local vertices `[0, 41)`. Vertices 41 through 48 remain unchanged. The first modifier displaces Y and Z using X as the wave input. Its amplitude is weighted by the **runtime alpha byte divided by 256**. The second displaces X and Y using the already modified Z coordinate. Both use the native 1024-entry trigonometric table with a quarter-cycle cosine offset.

**Correction after tracing the loader:** there is no `+2` weight conversion in the verified path. The previous comparison used GAO instance colors instead of primary mesh colors. Their alpha bytes happen to differ by two for these fixtures, but they are different buffers with different roles.

### Weight source and loading path

- `0043F120` loads the geometry resource and dispatches through `00435840`. Type 1 selects the geometry reader `00433500` through table slot `00A6E86C` (initialized at `004346F0`).
- For this PC geometry, the color-copy loop in `00433500` copies each packed source word unchanged to the allocation addressed by **mesh +0x14**, after its count word. The alternative byte-order branch is not a numerical alpha conversion.
- `006AB5A0` resolves the object's primary mesh and reads that same mesh color pointer. Its first weight byte is at color allocation +7 (four-byte count followed by RGB and alpha). This is not the instance color allocation used by `00432600` for prepared draw colors.
- In mesh `2E004CC0`, the 49 packed colors start at payload offset **632**, after 49 XYZ vertices; this mesh has no stored normal array. They match all four channels of every captured runtime color buffer exactly.
- The fixture GAO color block starts at payload offset 189. Its first alpha is 238, whereas the mesh alpha is 240. The animation uses **240 / 256 = 0.9375**, not 238/256, 240/255 or an adjusted instance alpha.

The replay now obtains weights exclusively from the mesh file, asserts exact equality with all 124 captured buffers (6,076 packed words / 24,304 bytes), and composes the second modifier over the independently calculated first result. Native phases are still supplied by the capture. This verifies the source and scaling of the weights for the frozen fixtures, not arbitrary engine versions or animation startup timing.

Private loader evidence is in `hangfire-weight-loader`, `hangfire-weight-loader2` and `hangfire-weight-loader3`; decompiled source remains outside the repository.

`integration_hangfire_modifiers.py` checks 62 observations of each modifier, their order, the frozen resource identity and the unchanged excluded vertices. Maximum local-coordinate error is `5.960464477539063e-08` for the first and `5.960464477539063e-08` for the second. These checks use captured phases; they do not establish startup timing or runtime parity.

The capture contains repeated records of `<IIfI>` (frame, flags, phase, vertex count), followed by 49 packed native colors and 49 XYZ float triples. Replay with:

```powershell
python tests/integration_hangfire_modifiers.py <local-capture>/hangfire-weights2-modifiers.bin <decoded-menu>/decoded.bin
```

## Lighting receiver audit

Across 31 sampled frames (0 through 360, step 12), the probe recorded 3,585 calls after color preparation at `00432600`, covering 68 runtime object pointers. It also recorded 341 calls to light accumulation at `00444A60`: 31 per object for 11 runtime objects.

Matching stored translations identifies the balcony, trunks and both hangfire fixtures among objects with cached instance colors and the dynamic-color flag cleared after preparation. For these measured draws, adding the named lights indiscriminately would risk applying illumination over already prepared colors.

The 11 accumulation receivers have positions clustered near the balcony and no cached color pointer. They have **not** been resolved to named scene objects. Their location alone is insufficient to identify them as the Prince. Matching by translation also cannot disambiguate every overlapping scene object.

This audit does not prove that all light contributions are baked, that every rendering path was captured, or that the existing Vulkan illumination is faithful. It narrows the next investigation to the actual receivers and the remaining glow effects, rather than an arbitrary global brightness change.

## Integration boundary and next work

- The fixture UV animations and both composed vertex modifiers now run in Vulkan; see the [integration and validation report](2026-11-10-vulkan-fixtures.md).
- Weight loading is verified: use the primary mesh alpha unchanged, divided by 256. The integration evaluates the modifier chain in order, in local coordinates, before the stored object transform.
- Identify the 11 dynamic-light receivers and capture their light lists and resulting colors.
- Audit the small glow objects and remaining unsupported scene components separately. Do not equate a decoded material with a completed light implementation.
- Prince animation, complete effect ordering and final visual parity remain outstanding.

This loading audit itself made no renderer or global-light changes. The subsequent fixture integration is documented separately above.
