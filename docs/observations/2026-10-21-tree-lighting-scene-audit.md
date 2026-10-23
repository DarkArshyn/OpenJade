# Tree lighting and stored scene transform audit

## Scope and reproducible case

This is a static investigation of the PC executable and the frozen Menu3D
resource, not a capture of the original game's live graphics state. Input hashes
are recorded in [native fog evidence](2026-10-21-native-fog-state.md).

The selected object is `Menu3D_tronc4.gao` (`30000CBC`), mesh `30000C6F`,
identity **3** in the diagnostic image. It is the narrower central-left trunk,
not the large far-left foreground trunk (identity 6, `Menu3D_tronc1`).
Its two groups use materials `30000C95` and `30000CA9`, selector 0, with
128 and 28 triangles. There are 82 instance color words; recorded RGB ranges
from `[3, 9, 12]` to `[39, 72, 109]`. No normal array was decoded for this mesh.

## Native branch evidence

- Loader `0067D8C0` reads the instance flags after the mesh/material keys and
  copies the counted color words into a runtime allocation. For this version-10
  descriptor the stored flags are `0x0D2255FF`; bit `0x40` is set.
- `00432600` tests that bit and a non-null instance color buffer. It selects the
  recorded colors at context `F238`, clears context flag `0x20`, and returns.
- `00432720` gates its subsequent dynamic light accumulation on that context
  bit. Consequently the selected recorded state takes a path that bypasses
  those light contributions. It does **not** simply add every scene light to
  this tree's recorded colors.
- Material selector 0 in `00441560` uses the prepared color pointer. The
  textured state in `006696B0` includes MODULATE2X. The complete vertex upload
  and possible intermediate scaling have not been traced; an unconditional
  factor-of-two correction to the preview is therefore not established here.
- Other conditional paths exist: `00441FB0` multiplies packed color channels
  using `(a * b) >> 8`; `00442050` combines packed colors with saturation;
  `00444A60` accumulates lights. Their existence does not establish that those
  paths run for this particular tree.

Local, ignored evidence: `reports/native-tree-lighting-20261021/` contains the
new loader and rendering exports; the earlier preparation functions are in
`reports/native-material-colors-20261021/`. These are local research evidence,
not source files to redistribute. Runtime mutation of the instance flags has
not been ruled out. The conclusion is conditional on the loaded state examined.

## Placement and screenshot comparison

`audit_menu_scene.py` inspects all **42 assembled objects**, exporting stored
translation, basis, scale fields, matrix flags, world bounds, instance flags,
color ranges and a numbered identity image. Fog is omitted from that image;
texture alpha is retained with the diagnostic renderer's threshold. Its visible
pixel bounds are not measurements of visibility in the original game.

For identity 3, the stored basis is identity, matrix flags are `2`, scale fields
are zero (unit scale in the current decoded convention), and translation is
`(-92.62071991, 0.48318568, -4.98725796)`. This verifies what is stored, not that
the runtime world transform is identical: hierarchy and animation remain open.

The supplied `02 - MenuPrincipal.png` is the original 800x600 reference.
The diagnostic still uses Camera02 with manual yaw +12 degrees, pitch -1 degree
and vertical FOV 50 degrees. Comparison shows remaining differences in balcony
framing, foreground trunk silhouettes, vegetation and brightness. The balcony
opening appears larger and higher in the diagnostic. These observations do not
uniquely identify a wrong object transform: camera projection, missing geometry,
hierarchy and animation can also affect the image. Menu text occludes some of
the reference scene, and the fog phase is not synchronized.

No object was moved, rotated or brightened to conceal these differences. In
particular, **all objects being correctly placed is not yet validated**.
Next verification should use several corresponding static landmarks together
(balcony opening corners and distinct trunk junctions) to constrain the camera,
then check any remaining per-object residuals. Brightness requires completing
the native vertex-color upload path before adding general lighting.

## Running and validation

```powershell
python -B .\src\audit_menu_scene.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\menu-material-colors-20261021 .\reports\menu-scene-audit-20261021
python -B .\tests\test_audit_menu_scene.py
```

The output directory must not exist. Outputs are `audit.json` and
`object-identities.png`; no game files are modified. Three synthetic tests check
the direct-color flag, a prefixed descriptor, absent/empty color cases and
rejection of truncated or inconsistent extents. The real-data run audits 42
objects. This is diagnostic coverage, not proof of visual equivalence.
