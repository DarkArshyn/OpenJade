# Missing menu objects and fog experiment

## Evidence and scope

Local frozen Menu3D decoded payload SHA256:
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
This work reads extracted data only. No original game files are changed.

Compared with the October 20 colored assembly, two objects are now accepted:

| Object | Triangles | Previous blocker |
| --- | ---: | --- |
| `Menu3D_FarahRoom_Balcony.gao` | 8,898 | Raw texture `6600D788` unsupported |
| `Menu3D_ground.gao` | 2 | Zero UV count rejected |

The assembly contains 41 objects and 14,956 triangles. Thirty-five material
textures are decoded; this includes resources discovered before an object is
excluded, so it is not a count of visible materials.

Format 0 pixels are interpreted as BGRA, after validating dimensions and the
exact extent of all declared mip levels. The 128x128 balcony texture has five
levels and a 56-byte header (87,352 bytes total). Channel interpretation remains
a reader interpretation, not a recovered native renderer specification.

Meshes with no UV array now retain their geometry and use constant (0,0) sampling
in this diagnostic renderer. This is not evidence that native texture coordinate
generation is understood. The sky still fails the transformation restriction.

## Fog experiment

`Menu3D_fake_fog.gao` and `Menu3D_fake_fog2.gao` use their decoded texture alpha,
UVs, transforms and stored RGB. They render after opaque geometry, with source-over
blending and depth testing but without depth writes. Ordering uses object-center
depth. Selection of this mode is explicitly name-based, not a decoded material
blend flag. No full-screen artificial fog layer is added.

`alpha-test-baseline.png` and `fixed-camera.png` use identical geometry and camera.
The only difference is this fog blend experiment. On this sample, 81,591 pixels
change, with a maximum channel difference of 15. The result remains substantially
darker and less misty than the supplied original screenshot.

Native blend factors, fog density, vertex-alpha semantics and other lighting
contributions are not established. Object sorting does not resolve intersecting
transparent triangles; shared-edge blending is also diagnostic. The third fog
panel remains excluded because its matrix contains unsupported auxiliary values.
Other exclusions include scaled objects and multi-stage light materials.

Camera yaw +12 degrees, pitch -1 degree and vertical FOV 50 remain manual
approximations from the previous experiment; they are not newly recovered values.
OBJ/MTL exports do not encode this experimental fog pass.

## Reproduction and validation

```powershell
python -B src/assemble_menu_scene.py <decoded.bin> reports/menu-scene-fog-20261021
python -B tests/test_menu_fog.py
python -B tests/test_menu_primary_geometry.py
python -B tests/test_assemble_menu_scene.py
```

The output directory must not already exist. The assembler checks the frozen
source hash. Reports contain original-derived assets and remain local.

Synthetic regressions cover BGRA channels and malformed extents, zero-UV geometry
and truncation, source-over values, opaque depth occlusion and layer ordering.
Next evidence target: the third fog panel's scale/transform fields and the native
material blend state, before claiming original fog fidelity.
