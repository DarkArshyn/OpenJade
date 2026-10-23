# Camera constraints and dynamic vertex-color upload

## Camera: a constraint, not a recovered native view

The reference is the user's original menu screenshot at 800x600.
Manual image correspondences are stored in
[`references/menu-camera-landmarks.json`](../../references/menu-camera-landmarks.json).
The three accepted landmarks are the central balcony decorative apex and the
two upper curtain corners. The right corner is partly occluded and has a wider
tolerance. These are approximate observations, not pixel-exact ground truth.

Two additional foreground silhouette candidates were initially included. The
annotated comparison revealed ambiguous foliage overlaps: they cannot reliably
be identified as the same trunk junctions. They are retained as **excluded
diagnostic candidates**, not as calibration constraints or validated holdouts.

| Fit | Yaw adjustment | Pitch adjustment | Vertical FOV | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Previous manual preview | 12 degrees | -1 degree | 50 degrees | Starting point |
| Initial five-candidate trial | 14.254 degrees | 0.349 degrees | 58.350 degrees | Rejected as calibration: two ambiguous correspondences |
| Three balcony landmarks | 13.606 degrees | 1.455 degrees | 53.413 degrees | Local framing constraint only |

For the accepted balcony landmarks, the final RMS residual is **1.58 pixels**.
The excluded foreground candidates have residuals **42.75** and **41.01 pixels**.
Those residuals may reflect incorrect correspondence, scene transforms, or camera
parameters; they do not prove that either tree must move. The initial trial's
46.34-to-13.18-pixel improvement across five candidates is not a valid accuracy
claim once those correspondences are questioned.

The fit keeps the stored Camera02 position, all scene geometry and object
transforms fixed, varying only yaw, pitch and vertical FOV. It maps rays from
the existing preview to the reference with the same pinhole projection as the
rasterizer. All three accepted points lie on one small feature, so they cannot
independently validate camera position, roll, runtime hierarchy or whole-scene
alignment. The sensitivity to candidate selection is why the default camera
has **not** been changed. The next useful evidence is another unoccluded,
unambiguous object feature or a captured native view/projection matrix.

## Colors: dynamic upload traced to submission

This extends the [selected-tree audit](2026-10-21-tree-lighting-scene-audit.md).
All executable addresses refer to the same hash-checked POP.EXE.

1. `00432600` selects the instance color array for the loaded `tronc4` state.
2. Mode 0 in `00441560` copies the prepared `F238` pointer to `1DC9C`.
3. `00425CF0` installs `006622D0` in the draw callback at offset `0x28`.
4. `006622D0`, when the group's cached buffer field is null, calls `006609E0`.
5. `006609E0` reads colors through `1DC9C`, applies an OR mask and an XOR
   mask, swaps the red/blue byte positions, and writes the packed word at
   vertex offset **24**, with a **36-byte stride** (position, normal, color, UV).
   There is no division or multiplication of RGB in this packing operation.
   The inspected static OR mask `00AE176C` is zero; mode 0 clears the XOR mask
   before the optional alpha handling. Runtime indirect changes are not excluded.
6. `0066F9E0` returns space in the CPU staging buffer. Constructor `0066F7A0`
   installs vtable `007B152C`; entry `007B1538` points to **0066F7F0**.
7. `0066F7F0` locks the vertex buffer, copies `count * stride` bytes unchanged,
   unlocks it, and advances its write position. `00663380` binds the stream and
   submits the primitive draw. This closes the dynamic CPU-to-GPU copy path.

The textured branch of `006696B0` uses operation 5, MODULATE2X, with diffuse
vertex color for mode 0. Microsoft documents this as twice the product of its
arguments ([D3DTEXTUREOP](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dtextureop),
consulted 2026-10-21). Thus the traced direct-color case calls for texture RGB
times recorded RGB times two, followed by saturation; a hidden divide-by-two
in this dynamic packing/copy path is ruled out.

**Limit:** `006622D0` also has a cached-buffer branch through `006688C0` and
`00668850`. Which branch the running game uses for this tree has not been
captured. The trace establishes the dynamic path, not every possible path or
every live render state. It does not establish whole-scene lighting parity.

## Bounded implementation and local outputs

`menu_gpu_colors.py` expresses packed-color conversion independently and checks
the exact loaded flags and two material keys for the selected-tree experiment.
`assemble_menu_scene.py --tree-upload-check` applies the resulting RGB factor
only to `30000CBC` (`Menu3D_tronc4`), leaving the rest of the scene unchanged.
The option is explicit and off by default. No global exposure compensation is
applied. Original game files remain read-only.

```powershell
python -B .\src\fit_menu_camera.py .\references\menu-camera-landmarks.json .\reports\camera-fit.json
python -B .\src\assemble_menu_scene.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\camera-fit-preview --yaw 13.60627541 --pitch 1.45480671 --fov 53.41335346 --tree-upload-check
python -B .\tests\test_camera_gpu.py
```

Local ignored evidence is under `reports/camera-gpu-20261021/`: camera fit JSON,
annotated original/comparison figure, initial and final preview folders, and
native decompiler exports. The fit JSON records source-image hashes. No original
screenshot, texture or native decompilation is bundled with the source code.

Four synthetic tests cover known-camera recovery, degenerate correspondences,
all 256 red-channel packing values and mask order, and the bounded tree case
with saturation deferred until texture modulation. Existing assembler and
material-color tests also pass. Real-data previews retain 42 objects and
14,960 triangles; framing changes do not change the source geometry.
