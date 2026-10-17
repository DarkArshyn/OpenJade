# Three-object assembly and camera hypotheses — 2026-10-17

The fixed-sample exporter `preview_menu3d_assembly.py` reads the previously
verified decoded menu3D scene only. It assembles ground (GAO 0x30000CCD / mesh
0x30000C80), fake_fog (0x30000CC7 / 0x30000C7A) and fake_fog2 (0x30000CC3 /
0x30000C76). The latter has six vertices and four triangles with the same verified
XYZ duplication, stride-20 and terminal uint16 index-list structure.

All three selected object bases are identity and their auxiliary fourth words
within the three axis groups are zero. Candidate translations are applied in a
shared coordinate space for this experiment. This is not proof of world-space
semantics or absence of a transform hierarchy. fake_fog3 is deliberately excluded:
its auxiliary values include 1, 1 and approximately 0.33019, so blindly treating
those values as padding would discard unexplained data.

## Camera comparison

Camera02, Balcony and Alternate candidate bases are orthonormal within 1e-5.
For Balcony and Alternate, normalized camera-to-target directions have row-axis
dot products approximately (0.0184,-0.9969,-0.0765) and
(0.0237,-0.9910,0.1321). Negative local Y differs from the target direction by
about 4.5 and 7.7 degrees, respectively. This supports forward -Y with basis rows
as a useful hypothesis; it is not an exact look-at relation or proof of convention.

The diagnostic projection uses local X horizontally, Z vertically and -Y for
depth, a chosen 60-degree vertical FOV and near distance 0.1. Neither projection
parameter is recovered from the game. Near-plane clipping is implemented for
wireframe segments. There is no texture, occlusion, lighting, animation or game
material behavior. The transparent ground candidate is deliberately visible as
a geometric outline, not presented as an opaque game surface.

The output compares three orthographic views and three perspective hypotheses.
No active camera is selected: these sparse objects are insufficient to match
the original screenshot. A recognizable landmark such as the balcony or a tree
is needed before comparing framing against the reference.

## Validation and outputs

Real-data checks cover source hash, vertex-array agreement, index bounds/extent,
identity object bases, translation invariance and camera orthonormality. Three
synthetic clipping tests cover fully hidden/visible segments, crossing and reversed
endpoints. All pass. The comparison sheet was visually inspected.

`reports/menu3d-assembly-20261017` contains `assembly-candidate.obj`,
`assembly.json`, individual camera PNGs and `assembly-comparison.png`.
JSON retains the decoded UV attributes even though this wireframe OBJ does not
apply materials. Reports remain excluded from Git. No new archive extraction.

```powershell
python .\src\preview_menu3d_assembly.py <decoded-scene> <new-output-directory>
python .\tests\test_assembly_preview.py
```
