# Dynamic-light receiver identities in the menu

Date: 2026-11-11

## Result

The eleven captured calls to the dynamic-light accumulation path per sampled frame resolve to **Prince-related render components**, not eleven missing fixed-background objects. Nine belong to `Prince.gao` (`CC000431`), one to `Prince_Head_LowRes.gao` (`330005EC`) and one to `Prince_Holder_WAY.gao` (`3F000E2F`).

The component labels below are verified GAO-to-mesh resource bindings. They should not be confused with the runtime parent: for example, `M_Pr_Face.gao` supplies the mesh used under `Prince_Head_LowRes.gao`. The exact role of the holder object is not inferred from its name.

| Component GAO | GAO key | Mesh key | Vertices | Runtime parent |
| --- | --- | --- | --- | --- |
| `Prince_Sword01.gao` | `0x057CC7FF` | `0x33001050` | 54 | `Prince.gao` |
| `Prince_Dagger.gao` | `0x057CC800` | `0x057CC7F4` | 83 | `Prince.gao` |
| `Prince_Holder_Body.gao` | `0x3F000E24` | `0x3F000E05` | 24 | `Prince_Holder_WAY.gao` |
| `M_Pr_Face.gao` | `0x13005EEA` | `0x13008483` | 294 | `Prince_Head_LowRes.gao` |
| `M_Prince_Plate_Body.gao` | `0x1300695C` | `0x13008426` | 160 | `Prince.gao` |
| `M_Prince_Legs.gao` | `0x1300695F` | `0x13008425` | 330 | `Prince.gao` |
| `M_Prince_Veil.gao` | `0x13006962` | `0x1300842C` | 220 | `Prince.gao` |
| `M_Prince_Plate_Shoulder_Left.gao` | `0x13006955` | `0x13008427` | 33 | `Prince.gao` |
| `M_Prince_Sleeve_Left.gao` | `0x1300695D` | `0x1300842A` | 175 | `Prince.gao` |
| `M_Prince_Plate_Shoulder_Right.gao` | `0x13006959` | `0x13008428` | 33 | `Prince.gao` |
| `M_Prince_Sleeve_Right.gao` | `0x1300695E` | `0x1300842B` | 175 | `Prince.gao` |

## Evidence chain

A new bounded capture of the same GOG research copy records 341 calls to `00444A60`, across 31 sampled frames (0 through 360, step 12). Every one of the eleven receiver pointers appears exactly 31 times.

At the accumulation call, the probe records the receiver, its geometry instance and primary mesh pointer, and the current parent at rendering context +0x90. It also snapshots the 5,000-entry deferred-load table at `007F1598`. Entries contain a resource key, destination slot, callback and flags; the probe reads the current value of each readable destination slot. `00420BF0` and `004207D0` establish this table's key/slot interpretation.

A unique `0067DF50` load binding resolves each parent pointer to its GAO key. A unique `0043F120` geometry binding resolves each primary mesh pointer to its resource key. The instance's own geometry pointer must agree with the recorded mesh pointer. Some render instances share geometry loaded through another destination slot; identity is therefore checked against the resolved geometry pointer, not by requiring the destination slot to equal the current render-instance address.

Three targeted archive resources were decoded using the existing bounded POP-LZO tools, with verified output hashes: Prince (`FF0C0226`), PrinceCostume01 (`FF030FA9`) and Prince_Weapons (`FF05C7FE`). No general archive analysis was performed. Their resource records provide the parent names, exact vertex counts and unique component GAO-to-mesh links shown above.

| Decoded archive resource | SHA-256 |
| --- | --- |
| `0xFF0C0226-decoded` | `6a2886cc69d194bbbd526184ca2a217c4575b43ffe7453fbeea2f0f151f1e7a5` |
| `0xFF030FA9-decoded` | `435657beb484850ac6c50c58dc3c78abd0e734f66ddff447bf0adbbe822d8941` |
| `0xFF05C7FE-decoded` | `20890d32a8715babc499a4799988d0ac7fa1537e452a0daa47867a8e39f41a9e` |

## Validation and limits

`tests/integration_light_receivers.py` checks unique required-resource identities, native load bindings, parent names, mesh vertex counts, unique component labels and the 341-call frame distribution. It also verifies that the earlier `hangfire-light` capture has the same call count and multiset of receiver vertex counts.

The old capture did not preserve resource keys. Its equal-size components cannot be uniquely assigned to historical pointers retrospectively. The identities above are established by the new capture of the same menu scenario; no cross-process pointer equality is assumed.

An accumulation call does **not** prove a nonzero contribution from a particular lamp. The effective private light lists, individual light parameters and resulting colors still require measurement. These identities do not justify increasing global brightness or adding lights over cached scenery colors. They also do not prove completeness of every rendering path outside the sampled interval.

Private evidence remains in the research workspace's `light-identify/` directory. The probe completed and the saved proxy was restored. The original installation was only read; no original assets or native code are added to Git. The viewer is unchanged by this identification step.

Reproduce from the repository root with the local evidence paths:

```powershell
python tests/integration_light_receivers.py <light-identify> <Prince-decoded.bin> <PrinceCostume01-decoded.bin> <Prince_Weapons-decoded.bin> --previous <hangfire-light>
```

## Consequence for the menu milestone

These receivers belong to the actor/equipment work rather than a missing set of eleven scenery lights. For the fixed menu background, the next independent target remains the small glow/halo effects. When implementing the Prince, retain the distinction between each render component, its owning GAO and the effective lights applied to it.

## Follow-up

The [GPU contribution measurement](2026-11-11-menu-light-contributions.md) now distinguishes selection from measurable per-draw RGB effects and identifies an additional generated directional contribution. The earlier identification result alone did not establish these effects.
