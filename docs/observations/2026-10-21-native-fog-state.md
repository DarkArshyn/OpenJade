# Native fog transform and material state

## Sources and reproducibility

Analysis date: 2026-10-21. Frozen PC GOG POP.EXE SHA256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Decoded Menu3D SHA256:
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.

Ghidra opened the saved project with `-readOnly -noanalysis`; the game was not run.
Selected decompiler exports remain in ignored local
`reports/native-fog-20261021/evidence/`. The independently written exporter is
`tools/ghidra/OpenJadeFog.java`; it takes a new output directory and hexadecimal
function entry points. Decompiled game code is not part of the source tree.

## Third panel transform

Object `30000D38`, `Menu3D_fake_fog3.gao`, uses mesh `30000C76` (four triangles).
Its row-basis rotation is identity, translation is
`(-88.248397827, 9.239985466, -3.127662420)`, and scale is
`(1, 1, 0.330190331)`. The matrix's last-row fourth word is not used as a
homogeneous coordinate.

Native evidence:

- Loader `004246D0` reads a 68-byte matrix; `0079BBB0` refreshes flags.
- `0079BA70` examines the scale triplet; `00798B90` obtains it from offsets
  `0x0C`, `0x1C`, `0x2C` when flag 8 is active, otherwise returns unit scale.
- `0079A080` multiplies each local coordinate by its corresponding scale before
  combining the basis rows. This establishes local-axis scaling, not world-axis
  scaling. The existing translation convention is retained in the assembler.

The resulting third-panel world bounds are approximately:
`(-88.805386, -11.795484, -4.216756)` to
`(-87.654334, 9.702992, -2.038569)`.
Only this newly verified scaled instance is enabled; other previously excluded
scaled objects remain outside this change. The assembly now has 42 objects and
14,960 triangles.

## Original material parameters

All three fake-fog objects select slot 24 of pack `30000CB3`, leaf `30000CAB`,
texture `30000C66`. The 48-byte version-6 leaf stores stage flags `0x40014205`
at offset 28 and packed color `0x6668543A` at offset 8.

| Parameter | Evidence-supported value |
| --- | --- |
| Blend mode | 1: source alpha / inverse source alpha |
| Depth writes | Disabled (`0x200`) |
| Alpha test | Disabled (`0x10` clear) |
| Alpha inversion | Disabled (`0x80` clear) |
| U addressing | Wrap (`1`) |
| V addressing | Clamp (`2` clear) |
| Linear filtering request | Set (`4`); actual native filtering also depends on quality settings |
| Color selector | `(flags >> 13) & 7 == 2`: material constant |
| Constant RGB | (58, 84, 104), from low-to-high color bytes |
| Texture color operation | MODULATE2X |
| Local alpha override | Disabled (`0x400` clear) |
| Dynamic U | Flag set; animation is not reproduced |

`00446480` loads the stage flags. Its legacy conversions apply to versions below
5, not this version 6. `00441560` case 2 selects material RGB and, with local alpha
disabled, sets the context alpha to 255. `00669330` transfers flags and the context
color to the graphics-state cache. `006696B0` emits the Direct3D state calls:
blend enable 27=1, source 19=5, destination 20=6; depth write 14=0;
alpha-test enable 15=0. The same function selects texture-factor color and
color operation 5 (MODULATE2X).

The numeric interpretations follow Microsoft Learn:
[D3DBLEND](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dblend),
[render states](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3drenderstatetype),
[texture operations](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dtextureop),
and [texture arguments](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dta),
consulted 2026-10-21. This is static path verification, not a GPU capture of a
running frame.

The later Jaded MATstruct.h and DX9renderstate.c were consulted at revision
`8d55704c80adfcec4f3bcaeb2445dc9f68ef960e` as search aids. TSoT's color-selector
shift differs from that later header, so its constants were not copied into the
implementation. See [provenance](../../references/jaded.md).

## Rendering result and limitations

The previous preview multiplied fog pixels by black stored vertex RGB. That was
incorrect for this material's constant-color mode. The new preview uses
`texture RGB * (58,84,104)/255 * 2` with texture alpha, base-level bilinear
wrap-U/clamp-V sampling and source-over. Fog selection now follows the resolved
material, not object names. Unsupported state combinations fail explicitly.

`reports/menu-scene-native-fog-20261021/fixed-camera.png` includes all three panels.
`alpha-test-baseline.png` uses the same corrected geometry/colors/sampling but
the old alpha-threshold path; it is not the previous turn's image.

Remaining limitations: manual camera adjustment, original general lighting,
other materials, dynamic UV transforms, mip selection, transparent-object ordering,
shared-edge rasterization and full scene hierarchy. The separate `Menu3D_Fog3D`
objects use another geometry type and remain excluded. The scene is still an
offline diagnostic and is not integrated with the interactive menu.

## Tests

Run `test_menu_fog_state.py`, `test_menu_fog.py`,
`test_menu_primary_geometry.py` and `test_assemble_menu_scene.py` with Python.
Twelve synthetic checks cover state decoding/refusal, color channels, scale
ordering, nonfinite rejection, sampler boundaries, alpha compositing/depth,
primary geometry and raw texture bounds. The real-data assembly also validates
the frozen source hash and reports exclusions in `scene.json`.
