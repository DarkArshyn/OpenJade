# Per-material color dispatch in the menu scene

## Scope and result

This step corrects constant-color selection outside the fog panels. It does not
introduce an exposure adjustment or reconstruct general scene lighting.
The frozen input hashes are those in [native fog evidence](2026-10-21-native-fog-state.md).

The scene still has 42 objects / 14,960 triangles. Nine non-fog face groups across
seven objects (200 triangles) use selector 2:

- `Menu3D_chemin` and `Menu3D_fake_buisson`: 16 triangles each.
- `Menu3D_FarahRoom_Balcony`: three groups totaling 40 triangles.
- Four `Menu3D_rido` instances: 32 triangles each.

These groups now use their material RGB multiplied by two with the texture,
instead of the object's stored vertex RGB. Fog groups retain the same rule.
Expanded primary corners keep color assignments isolated between material groups.
Values are saturated after texture modulation, not before it.

## Evidence

Previously inspected TSoT function `00441560` switches on `(flags >> 13) & 7`.
Case 2 selects the material's low 24 color bits. `006696B0` selects texture-factor
color and MODULATE2X. These paths are documented in the native fog study and
apply to the same version-6 single-stage material layout outside fog.

Other observed selectors are 0 and 3. New static investigation identified:

- `00432600`: prepares the color-buffer pointer at render-context offset `F238`.
  Depending on flags it can reference instance colors, copy them, or clear the
  working buffer; it also sets a separate geometry-color pointer.
- `00441560`: mode 0 selects the working buffer; mode 3 selects that separate
  geometry-color pointer. Neither is universally equivalent to the assembler's
  unconditional instance-color preference.
- `00444A60`: can add contributions from scene lights into the working buffer,
  with branches depending on light type, normals and object state.

The exact active branches for the menu have not been established. Modes 0 and 3
therefore retain the prior vertex-color approximation and are explicitly marked
unresolved in the report. No global brightness multiplier is applied to them.
General material alpha, filtering, UV transforms and runtime light contributions
remain outside this correction.

Ghidra used `-readOnly -noanalysis`; the executable was not run or modified.
Local exports are in `reports/native-material-colors-20261021/`, excluded from Git.

## Output and validation

```powershell
python -B src/assemble_menu_scene.py <decoded.bin> reports/menu-material-colors-20261021
python -B tests/test_menu_material_colors.py
```

`fixed-camera.png` is the corrected rendering. `previous-colors.png` uses exactly
the same scene and camera with previous color handling. Its SHA256 is
`02c84e58a530a58747590500f38388f03d888cc5b08577d24bd15bc4f6c3c854`, identical to
the previous phase-zero fog render. `scene.json` records each decoded material's
selector and each accepted object's face-group color decisions, including
unresolved cases. Materials discovered for subsequently excluded objects may
also appear in the material inventory.

Three new regression tests cover layout rejection and selector decoding, mixed
groups without color leakage or input mutation, and preservation of unresolved
modes. Together with the existing geometry and fog checks, 18 tests are run.

The next evidence target is the actual mode-0 lighting path for one prominent
tree or wall: establish its instance flags, normals and contributing lights
before extending lighting behavior to the rest of the scene.
