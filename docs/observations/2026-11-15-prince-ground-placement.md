# Prince ground-placement investigation (2026-11-15)

The prepared scene and the existing 30-second native capture were inspected without
changing game resources, runtime rendering or actor placement.

| Quantity | Observed Z (scene units) |
| --- | --- |
| Source checkpoint origin | 1.356400489807129 |
| Native body origin, 167 samples | 1.342055082321167 to 1.3420555591583252 |
| Visible balcony triangle below checkpoint | 1.312741756439209 |

The native origin varies by less than 4.77e-7 across the sampled frames 0..1992.
The downward checkpoint difference is about 0.014345. However, the native origin
still sits about 0.029314 above the visible surface. These differences alone do not
establish a collision margin, capsule radius or ground-correction algorithm.

The intersected rendered triangle begins at vertex 35754, draw 47, belonging to
`Menu3D_FarahRoom_Balcony.gao`, material `30000C9F`, according to the prepared
manifest. Vertical intersection uses XY barycentric coordinates and interpolated Z.
Another hit at Z -1.098596 is lower and is not selected as a support surface.

At animation time zero, expanded actor vertex 4648 is the lowest vertex. Its
checkpoint-placed coordinates are approximately (-103.00668, -4.526744, 1.3528403).
The visible triangle below that XY starts at vertex 35979, also draw 47 and
Z 1.312741756. Thus aligning the actor origin directly with this visible floor
is not supported. Even substituting the captured origin leaves the lowest vertex
about 0.025753 above the visible surface at this pose. This is not proof of a game
bug: rendered and collision geometry, support shapes and offsets may differ.

`src/measure_prince_ground.py` reproduces the origin/surface comparison using local
prepared scene, placement sidecar and native capture. It refuses an existing output.
The intersection routine was checked against a synthetic tilted plane (known height
1.75) and an outside point. It does not decode native collision geometry.

```powershell
python src/measure_prince_ground.py $menuScene $assembledMenuDirectory $nativeCaptureDirectory $newReport
```

Private numeric results: `reports/prince-sheath-loop-20261115/ground-validation.json`.
Scene SHA-256: `8feda14c254b69c385f8b9f76f9bca72ca4365e6fcf25cdbcb7008f80e4f0e3e`.
Placement capture SHA-256: `0f8fcbd448eb3f0f2212ce7e708d1c963d13627b8b726ec05cb41834fbdc10a6`.

No height correction is applied. The next targeted investigation is the native
write to the actor world translation during initialization/grounding, and the
support or collision resource consulted by that calculation. The existing frame
timing reference remains unchanged because no runtime code is changed here.

Follow-up: [native writes and collision geometry](2026-11-15-prince-native-ground.md)
identify the distinct supporting triangle and explain the measured height.
