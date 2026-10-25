# Missing courtyard objects

Analysis date: 2026-10-25. Source: the same frozen decoded Menu3D as the
[projection correction](2026-10-25-camera-projection-sign.md), SHA256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.

## Findings

`material-15` in the previous render maps to material `30000CAF`, texture
`30000C69`, used by eight triangles in `Menu3D_liane.gao` (`30000CCE`).
The complete object has 50 triangles: 42 use `30000C95`, eight use `30000CAF`.
It was rejected by the assembler's nonzero-scale guard, not by the camera.
Its local scale is (1.3146404028, 1.3146404028, 1.3146404028).
The native local-scale-before-rotation convention already traced for the
[fog panel](2026-10-21-native-fog-state.md) applies to these same matrix fields;
`0079A080` was checked again in the local native evidence export.
No world position, camera pose or UV mirroring was introduced.

The assembler now enables this transform for the liana and the two named
hangfire objects only, alongside the previously supported fog panel.

| Object | Key | Retained triangles | Omitted triangles |
| --- | --- | ---: | ---: |
| Menu3D_liane.gao | 30000CCE | 50 | 0 |
| Menu3D_hangfire2.gao | 30000D53 | 4 | 56 |
| Menu3D_hangfire1.gao | 30000F45 | 4 | 56 |
| Menu3D_lampions.gao | 3000FCFA | 104 | 440 |

The fixture omissions are 72-byte multi-stage materials `2E00541D` and
`3000FCCE`, outside the current 48-byte single-stage decoder. Previously one
unsupported group excluded the entire object. For these three named fixtures,
only unsupported groups are now omitted, with material key and triangle count
recorded in `scene.json` under `omitted_groups`. This is partial geometry,
not complete fixture reproduction or reconstructed light emission.

## Validation and rendering

The render now contains 46 objects and 15,122 triangles. A comparison of reports
confirmed that all 42 previous objects retain their triangle counts and material
groups, and all four additions retain/omit the counts above. Camera report fields
match the previous horizontal-angle experiment exactly. Three existing fog
state/transform tests and two projection tests pass.

Local ignored artifacts: `reports/menu-missing-objects-20261025/renders/`.
`comparison.png` shows original, previous render and new render. The vertical
FOV remains approximately 59.38 degrees, with zero manual yaw/pitch adjustment.
This is a provisional projection hypothesis, not a verified live projection.

The liana now spans the upper image, including the upper right. Exact alignment
with the reference remains unvalidated. Lighting, alpha handling for non-fog
materials and camera motion state still limit the comparison. Next: decode the
fixture multi-stage material operations before claiming complete supports,
and resolve the actual projection branch before further camera fitting.
