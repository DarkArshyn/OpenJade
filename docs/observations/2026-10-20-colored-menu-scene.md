# Primary meshes, stored colors and approximate framing — 2026-10-20

The assembler now reads primary vertex/UV arrays and separate triangle indices,
instead of requiring a cooked 20-byte vertex buffer. It accepts 39 objects and
6,056 triangles, compared with 26 / 4,026 previously. Sixteen of the 55 geometry
candidates remain excluded; reasons are retained in scene.json. Skin metadata is
skipped structurally to reach base geometry; skeletal animation is not evaluated.

Stored RGB is decoded per object instance when a uniquely validated GAO color
array is found (matching vertex count, bounded extent, validity bytes and trailing
marker). This matters because objects sharing geometry can have different lighting.
37 accepted objects use instance RGB, one uses geometry RGB, and one explicitly
falls back to white. The rasterizer interpolates RGB perspective-correctly and
multiplies texture samples. Validity bytes are not used as opacity. This does not
reproduce dynamic lighting, gamma, native material modulation or fog.

The external comparison used FulGerNet/pop-bf-lab's
[mesh_parser.py](https://github.com/FulGerNet/pop-bf-lab/blob/main/bf_lab/mesh_parser.py)
and [jade_mesh.py](https://github.com/FulGerNet/pop-bf-lab/blob/main/jade_mesh.py),
consulted 2026-10-20. These links are moving references. Independent bounded
readers were written; no external module is imported. External interpretations
remain hypotheses corroborated by array extents, index ranges and visible results
on the frozen Menu3D data.

## Camera comparison

The user-provided 800x600 main-menu screenshot was inspected. The bright
balcony opening was used as an approximate visual anchor. Relative to the stored
Camera02 basis, yaw +12 degrees, pitch -1 degree and vertical FOV 50 degrees place
its approximate center near (346,190), compared with approximately (350,190) in
the reference. These are manually estimated pixels, not automated measurements.
The original baseline placed the opening around (465,220).

This is a one-anchor manual adjustment, not a recovered camera or a multi-point
calibration. Tree overlap, opening width and full perspective still differ. The
position remains the stored Camera02 position; hierarchy is unresolved. Options
--yaw, --pitch and --fov retain explicit control; --yaw 0 --pitch 0 --fov 60
reproduces the previous camera convention with the new geometry/colors.

## Reproduction

```powershell
python .\src\assemble_menu_scene.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\menu-colored-new
python .\tests\test_menu_primary_geometry.py
python .\tests\test_assemble_menu_scene.py
```

Output includes the image, OBJ/MTL, textures and a detailed report. OBJ vertex
lines additionally contain RGB (an extension not supported by every OBJ reader).
The 32 exported materials can include materials belonging to subsequently excluded
objects. Game resources are unchanged. Local output:
`reports/menu-scene-colored-20261020/`.

Three new tests cover separate UV indices, invalid indices/truncation and
instance-specific colors. Existing assembly tests are also retained. Original
screenshots and game-derived outputs are not added to Git.

Remaining work: unsupported materials/textures, six rejected object transforms,
and full fog/blending. The preview is visibly darker than the reference; no
arbitrary brightness correction was applied to conceal missing render behavior.
