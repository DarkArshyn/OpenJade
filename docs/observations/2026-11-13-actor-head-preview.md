# First frozen Prince component rendered in Vulkan

Date: 2026-11-13

## Result

The existing Rust/Vulkan viewer now renders a prepared, isolated sample of `M_Pr_Face.gao`, mesh `13008483`: 550 triangles, 417 stream vertices, 383 referenced vertices, and a 512x512 texture. The pose and per-vertex illumination are reconstructed by the research exporter from a captured native draw.

This is a **frozen diagnostic**, not a native actor loader, a runtime skinning implementation, or a complete Prince integrated into the menu. The Vulkan backend itself is unchanged. Original capture data, texture images and generated packages remain local under ignored research directories.

## Native reference and reconstruction

The GOG research probe selects the head by its same-session geometry load binding. It records the input stream, indices, three-weight skeletal palette, lighting constants and the active texture. The head's texture cannot be locked directly (`8876086C`); copying its surface into a temporary render target and reading that target succeeds. The exported texture preserves its original 512x512 dimensions.

For the reference image, the original game shader draws this component into a separate 800x600 target with its own cleared depth buffer. Only the projection is changed to frame the component, and fog is disabled. The original light-space matrices, skinning constants, textures, material state and lighting remain active. The original target, depth surface, viewport, projection constants and fog state are restored before normal rendering continues.

The independent Python exporter reconstructs the posed vertices and normalized-normal lighting using the [validated shader equations](2026-11-13-ambient-cache-shaders.md). It writes the resulting view-space geometry, captured UVs and per-vertex RGB into the bounded OJSCN003 interchange format. A diagnostic black background plane matches the isolated native target's black clear. The renderer applies the measured texture/diffuse modulation gain of two. Geometry identities and draw/state bounds are checked before export.

The lighting and pose remain frozen at export time. The largest unclamped lighting channel is approximately 1.188; the diagnostic clamps the vertex diffuse RGB to [0,1] before interpolation. The comparison validates this combined configuration for this sample, not every possible diffuse saturation case.

## Raster-center comparison

The first direct comparison had a mean absolute RGB difference of approximately 2.659 byte levels over the union of nonblack pixels. An explicit +0.5-pixel viewport correction in both image axes reduced it to approximately 0.209. The final exporter expresses that correction in the derived view-space vertices of this isolated sample. Original captured positions are never changed.

This measured correction is consistent with the Direct3D 9 versus Vulkan raster-center convention. It is scoped to the 800x600 diagnostic, recorded as `pixel_center_offset` in the manifest, and is not silently applied to the menu camera or scenery. `--pixel-center-offset 0` reproduces the uncorrected comparison.

## Final GPU validation

The final package was rendered through `jade-viewer --validation` with the legacy UNORM color pipeline. Two fixed-time frames were byte-identical, and no Vulkan validation errors were reported.

| Measurement | Result |
| --- | --- |
| Native nonblack pixels | 33,247 |
| Vulkan nonblack pixels | 33,230 |
| Silhouette intersection over union | 0.9994285 |
| Mean absolute RGB error over the union | 0.208975 / 255 |
| Maximum channel difference | 43 / 255 |
| Pixels differing in at least one channel | 4,018 |

These measurements compare isolated rendered pixels, unlike the earlier CPU arithmetic replay. The output is close but not pixel-identical. Residual sampling, rasterization and numeric differences have not been individually attributed. This result does not establish full-menu parity, fog integration, animation fidelity or a portable GPU tolerance across all drivers.

## Local reproduction

Export with Python, NumPy and Pillow, using the private completed `actor-head2` capture directory:

```powershell
python src/export_actor_head_preview.py <actor-head2> reports/actor-head-20261113
```

The exporter refuses to overwrite an existing output directory. The generated manifest records the native inputs' SHA-256 hashes, geometry counts, camera, raster correction and limitations.

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/actor-head-20261113/head.ojscene --color-pipeline legacy-unorm --validation
```

Run the screenshot-layer comparison into a new directory:

```powershell
python tests/integration_actor_head_vulkan.py reports/actor-head-20261113/head.ojscene reports/actor-head-20261113/gog-reference.png reports/actor-head-20261113/new-validation
```

This check requires the local Vulkan screenshot layer. It verifies fixed-time repeatability, validation output, silhouette overlap and bounded pixel error. The completed evidence is in `reports/actor-head-20261113/validation/`, including `comparison.png`, `comparison.json` and `validation.txt`.

The research-copy proxy was restored after capture; its hash matches the saved original (`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`). No original installation files were changed.

## Remaining work

- Resolve the captured head texture back to its original archive resource rather than relying on a GPU readback.
- Export actor geometry and transforms directly from original resources, with traceable skeleton/pose inputs.
- Move skinning and actor lighting into the runtime, then integrate the remaining components and material variants.
- Compare the complete actor in the menu with original depth, fog, occlusion and animation.

The frozen sample should remain a reference fixture while those runtime capabilities are implemented.
