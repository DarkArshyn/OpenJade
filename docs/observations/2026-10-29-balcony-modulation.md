# Balcony color modulation experiment — 2026-10-29

## Scope and result

A bounded comparison of `Menu3D_FarahRoom_Balcony.gao` (30000CD9), mesh
30000C8C, material pack 30000CB3. No global exposure change, camera change,
new light or default rendering change was made. This is an opt-in hypothesis,
not a verified reconstruction of the original lighting.

The raw frozen Menu3D resource contains 10,731 instance colors starting at
payload byte 197; instance descriptor flags are 0x0D2255FF. RGB byte ranges
are [0,1,2] to [211,177,175]. This mesh has neither a geometry color array nor
a stored normal array in the decoded primary layout. The exporter expands
8,898 triangles: 8,858 use mode 0; 40 use mode 2 constants.

## Evidence chain and remaining uncertainty

- `00432600`: with instance flag 0x40 and a non-null loaded color pointer,
  select recorded instance RGB and clear the dynamic-light-enable bit.
- `00441560`: material selector 0 chooses the prepared color pointer.
- The previously traced dynamic upload `006609E0` repacks channels without
  multiplying RGB; see [upload investigation](2026-10-21-camera-fit-gpu-upload.md).
- `006696B0` selects texture color operation 5 (MODULATE2X) when textured.
- Reinspection of `006688C0` confirms the cached draw path also calls
  `006696B0`, before `00668850` submits the cached geometry. This closes the
  question of whether that branch calls the material-state function; it does
  **not** establish how the cached vertex colors were populated.

These are static observations from the original executable, not a live capture
of the menu's selected render path. Instance flags can change at runtime.
Consequently, doubling the balcony's mode-0 modulation remains an experiment.
Do not double mode-2 colors again: their x2 is already represented in vertices.

Local evidence: frozen decoded.bin SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`;
`reports/native-material-colors-20261021/00432600.c`;
`reports/camera-gpu-20261021/tree-gpu-cache-native/006688c0.c`;
`reports/native-tree-lighting-20261021/tree-render-native/00668850.c`;
`reports/native-colors-20261028-constants/006696b0.c`.
Decompiled evidence stays in ignored local reports, not implementation source.

## Reproduce

From the repository root (Python with Pillow):

```powershell
python src/export_engine_materials.py reports/menu-fixture-materials-20261025/renders/horizontal-angle reports/camera02-transition-20261026/preview/poses.json reports/balcony-modulation-20261029/baseline
python src/export_engine_materials.py reports/menu-fixture-materials-20261025/renders/horizontal-angle reports/camera02-transition-20261026/preview/poses.json reports/balcony-modulation-20261029/modulate2x --balcony-modulate2x
```

Export requires a new output directory. Existing reports are never overwritten.
Run each package separately with the same settings:

```powershell
engine/target/debug/jade-viewer.exe --scene reports/balcony-modulation-20261029/baseline/menu.ojscene --color-pipeline legacy-unorm --texture-filter linear --gamma 0 --validation
engine/target/debug/jade-viewer.exe --scene reports/balcony-modulation-20261029/modulate2x/menu.ojscene --color-pipeline legacy-unorm --texture-filter linear --gamma 0 --validation
```

No menu bundle: no persisted profile/display settings or UI occlusion. Initial
viewport is 800x600, FOV 59.37908 degrees, initial Camera02 pose, fixed fog phase.
Zero gamma uses the recovered ramp; it is not mathematically identity.

## Validation and visual observations

- Four synthetic material export tests pass, including isolation from other
  objects, mode 2/3, multistage materials and the disabled experiment.
- Regenerated baseline is byte-identical to the prior texture package:
  `4255ee97ae1294371cbdb2832b69aacd03196b7f24aa842545bc84aa715bec6f`.
- Full binary comparison: only the gain fields of 13 balcony draws differ.
  Geometry, camera, image bytes, other passes and mode-2 constants are identical.
- Both exports retain 46 objects, 15,674 geometry triangles, 16,226 submitted
  triangles, 88 passes and 38 textures.
- Variant Vulkan smoke: 80 frames, zero validation errors, including resizes.
- Actual 800x600 viewport captures are saved locally as `before.png` and
  `after.png` in `reports/balcony-modulation-20261029/` (window chrome included).
  Window focus/cursor differ; these captures are not a pixel-difference metric.

Visual comparison with the user's original FR 800x600 menu screenshot:
architectural surfaces brighten in the experiment, but the opening remains
warmer and less veiled than the original. The full scene remains visibly
different. This experiment does not establish correct lighting or fog.

Next: trace cached color-buffer population for this object, then isolate fog
attenuation over the balcony, keeping camera and color arithmetic fixed.
