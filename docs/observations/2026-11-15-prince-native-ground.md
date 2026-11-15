# Native Prince grounding and balcony collision (2026-11-15)

## Verified native write

Hardware write observations on the rendered legs first identified a temporary
animated transform and the root-matrix copy in `006938B0` (post-write IP
`00693A49`). Following the copy source identifies the actual actor root. Contact
resource links identify that actor as `CC000431` (`Prince.gao`), not the legs mesh.

The observed update writes include post-write IPs `006B43C7`, `0069036B`,
`0069084C`, then `006E63AC`. The final write belongs to `006E61F0`, called from
`006E78DF` (return address `006E78E4`). These addresses are for the previously
hashed PC GOG executable only. Post-write IP is not necessarily the first byte
of the writing instruction.

A targeted wrapper around that call captures the segment endpoints, candidate
contacts and resulting matrix. The first captured call, at frame zero, records:

| Quantity | Value |
| --- | --- |
| Root Z before final adjustment | 1.3556004762649536 |
| Segment start Z | 1.4306005239486694 |
| Segment end Z | 1.0556004047393799 |
| Selected contact fraction | 0.2361205667257309 |
| Resulting root Z | 1.342055320739746 |

The source checkpoint Z is 1.356400489807129. Therefore the root has already moved
slightly before this captured call; the full startup/force chain is not yet decoded.
The measured final position equals the segment interpolation at the selected
fraction. Across 30 calls, maximum XYZ error of this independent arithmetic check
is 3.7461e-8. This validates the final adjustment, not a general collision solver.

## Resource-backed collision surface

The native contact pairs actor `CC000431` with `30000CD9`,
`Menu3D_FarahRoom_Balcony.gao`. Its final resource reference is `30000D18`, whose
eight bytes refer to collision geometry `30000D19`.

The focused geometry layout has 84 vertex positions, 130 normals and 130 indexed
triangles. There are 1,240 trailing bytes whose meaning is not decoded here.
`src/prince_ground.py` rejects other layouts; it is not a general format reader.
The same original object's XYZ transform maps the local collision vertices into
world space. No observed height constant is used to generate these vertices.

At the checkpoint XY, exactly one decoded collision triangle intersects the
vertical line: triangle 10, vertex indices `[13,14,1]`, upward normal `(0,0,1)`.
Its height is **1.342055320739746**, matching the selected native contact. The
contact's triangle field is also 10 in all 30 selected samples. The local plane is
approximately -5.210243 and the object's Z translation approximately 6.5522985.

The rendered surface previously measured at 1.312741756 is lower by approximately
0.029313564. The visual and collision meshes are distinct. This explains why
aligning the actor directly to the rendered surface would be incorrect.

## Reproduction and boundaries

```powershell
python src/prince_ground.py $decodedMenuBundle $newGeometryReport
```

Private captures and numeric reports: `reports/prince-native-ground-20261115`.
Geometry SHA-256: `32c19b2ce96d828d0f60d417a9a623d43edde1d682466e0c8e7db32337d23ba2`.
Contact capture SHA-256: `0fc8c5e2d7b04bd0ce42676393e1f29a8bba771153161e560ab72882c754112f`.
The research-copy proxy was restored and its hash verified. Original installation
data and historical engine source directories were not modified or used as code.

This update adds research decoding and evidence only. The existing prepared Vulkan
scene still uses the checkpoint height. The next integration can place the initial
actor using the validated source collision intersection, explicitly scoped to this
menu placement; continuous player collision, the full startup chain and movement
remain separate work. No runtime performance change is introduced here.

Follow-up: [the grounded placement is now integrated](2026-11-15-prince-grounded-integration.md)
in a newly prepared menu package. Earlier packages retain their original placement.
