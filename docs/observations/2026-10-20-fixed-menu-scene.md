# Fixed-camera menu assembly — 2026-10-20

The frozen Menu3D resource now produces a textured diagnostic assembly without
Blender: 26 accepted objects, 4,026 triangles, and 30 decoded leaf materials.
Some materials were decoded before their owning object was excluded, so the
material count includes unused exports. All source reads are read-only.

## Validation and scope

The reader discovers candidate 20-byte cooked vertex buffers and accepts exactly
one per mesh after checking buffer extents, material-group counts, triangle
indices, finite values and exact XYZ membership in the primary geometry.
It uses the previously tested landmark reader. This is a bounded discovery
method for the frozen resource, not a general mesh-format implementation.

Material packs use kind 4 with an exact key-array extent; supported leaves are
48-byte kind-5/version-6 records. The texture reference is at payload offset 44.
Repeated texture keys are resolved by requiring exactly one supported pixel
payload, rather than arbitrarily selecting the last record. BC1/BC3 top mipmaps
use the previously inspected layouts. Other formats remain excluded.

Object placement applies the stored three basis rows and translation in a
hypothesized common coordinate space. The last word of the fourth row remains
opaque and is not treated as an affine coefficient. Nonzero auxiliary words in
the first three rows are unsupported. Hierarchy and runtime updates are not
reproduced.

Of the earlier 55 mesh/header candidates, 26 are assembled. The other 29 fail
mesh-buffer validation (21), texture resolution (3), leaf-slot validation (2),
or transform validation (3). The other 54 GAOs have no direct link (37) or an
unsupported geometry header (17). Every exclusion is recorded in scene.json.

## Output and limitations

The 800x600 image uses fixed Camera02 (30000CF0), forward -Y and a chosen
60-degree vertical FOV. This is not a recovered main-menu camera configuration.
421,145 pixels receive geometry in this diagnostic view. Visual inspection shows
walls, palms and vegetation, but substantial differences from the reference remain.

Lighting and vertex colors are absent; nearest sampling, repeated UVs and alpha
testing at 128 are diagnostic choices. Fog blending, particles, animation and
original material states are not implemented. Consequently this is neither a
faithful final render nor a complete scene. No menu-viewer default is replaced.

```powershell
python .\src\assemble_menu_scene.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\menu-scene-new
python .\tests\test_assemble_menu_scene.py
```

Outputs: fixed-camera.png, scene.obj, scene.mtl, material PNGs and scene.json.
OBJ uses flipped V for interchange; rasterization retains the native UVs.
The output directory must be new. Local validated output is
`reports/menu-scene-fixed-20261020/`; game-derived files remain excluded from Git.
Three synthetic tests cover valid geometry, index bounds, XYZ disagreement,
material-array extents and short textures. The real-data run and image were checked.

Next priorities: decode the rejected geometry buffers and preserve vertex colors,
then compare fixed-camera framing with the user's 800x600 capture. Do not infer
camera activation or material blend states from this preview.
