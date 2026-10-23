# Comparison with the user-provided PoP BF Lab scene export

## Inputs and method

Compared OpenJade's `reports/menu-material-colors-20261021/scene.obj` against
the user-provided `reports/pop-bf-lab-menu/obj-jade-zup/menu3D_wow_ff000cb9.obj`.
Both represent the frozen Menu3D resource in Jade Z-up coordinates.
The report records SHA-256 hashes of both input files. Neither input was changed.

Objects are matched by their full GAO name, requiring exactly one matching
Lab object. OBJ face indices are resolved into ordered triangle corner positions.
The comparison checks triangle counts, ordered corners, unique positions,
bounds, and bidirectional nearest-position distances. Coordinate differences
are measured in the exported scene units; no physical unit is assumed.

## Results

All **42 OpenJade objects** have a unique counterpart. All have equal triangle
counts and matching ordered corner positions within **0.000001 scene unit**.
The largest absolute coordinate difference across all ordered corners is
`4.998931899535819e-7`, consistent with decimal rounding of the Lab OBJ output.
No realignment, scaling, rotation, translation or vertex reordering was applied.

| Selected object | Triangles in each export | Maximum absolute corner-coordinate difference |
| --- | ---: | ---: |
| Menu3D_tronc4 | 156 | 4.82e-8 |
| Menu3D_FarahRoom_Balcony | 8,898 | 5.00e-7 |
| Menu3D_fake_fog | 8 | 3.86e-7 |
| Menu3D_fake_fog2 | 4 | 4.24e-8 |
| Menu3D_fake_fog3 | 4 | 2.80e-8 |

The third fog panel's transformed geometry agrees, including the previously
decoded non-unit scale. There is no evidence here for moving or rotating these
objects to compensate for screenshot differences.

## What this does and does not establish

This cross-check supports the stored-geometry interpretation used by both
readers. It does not independently prove the original game's runtime world
transforms, visibility, hierarchy, animation, camera projection or lighting.
The two readers can share an interpretation that still needs native validation.
UVs, normals and material parameters were not compared in this step.

The Lab export has 109 named objects, including technical representations.
Subtracting 42 does not establish that 67 visible objects are missing from
OpenJade. The exported GLB contains no camera entries, no light extension and
no COLOR_0 attributes; its camera/light names refer to mesh representations.
It therefore does not resolve our native camera or recorded-color questions.

## Evidence and next investigation

Local ignored evidence: `reports/lab-geometry-comparison-20261022/` contains
`lab-object-comparison.json` and the independently written comparison script.
Run the script with the project Python environment to regenerate the report in
the current directory; it reads the two original export paths above.
These reports contain game-derived coordinates and remain outside source control.

Next, prioritize the native camera view/projection path, plus a separate
UV/material comparison. The geometry agreement argues against further arbitrary
object-placement adjustments. The earlier balcony-only camera fit remains a
local image constraint, not a validated whole-scene calibration.
