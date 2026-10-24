# Camera candidate list population and named menu zones

Date: 2026-10-24. Static, read-only analysis of the executable and the
frozen Menu3D decoded container. No live execution or camera pose is established.

## Registration and candidate insertion

| Function | Verified action |
| --- | --- |
| `004B0F00(manager, zone)` | Reads zone field `+0xA4` through `00549CC0`; skips value 2, checks duplicates, appends to manager `+0x34 + 4*count`, increments count `+0x4E4` |
| `005AE070` | If its object's field `+0x8C` is nonzero, registers the current object with manager key `B60024ED` |
| `0062D4E0` | Registers the current object on event discriminator `0x6E` |
| `004B0AC0` | Scans the manager list, applies conditional tests, and passes qualifying zone references to `005AC700` using camera pointer `+0x4F8` |
| `005AC700(camera, result, zone)` | Excludes current `+0x410` and duplicates, finds a free slot among eight entries at `+0x4EC`, writes the zone and sets `+0x6E4` and result to 1; otherwise result is 0 |

The manager append store is at `004B0FB8`; the camera insertion store is at
`005AC7D7`. The manager diagnostic identifies this as a zone array with capacity
300. Its full-array branch emits a diagnostic, but the decompilation still shows
an append afterwards: it must not be described as a verified bounds-safe API.
`004B0700` only searches the registered list and sets selected index `+0x14`.
`00627D50` clears its 300 entries; it is not an insertion path.

`00473390` returns current-object context `00ABC930`. Thus the registration
callers pass their owning object, rather than a hard-coded Camera02 reference.
The native key/pointer table gives `32000010 -> 005AE070` and
`B60024E7 -> 0062D4E0`. Both are typed OFC entries in behavior list `B60024E9`.

## Named objects in Menu3D

| Named GAO | GAO key | Wrapper | Instance |
| --- | --- | --- | --- |
| `Menu3D_FarahRoom_CAM_Balcony.gao` | `30000D63` | `30000D62` | `30000D61` |
| `Menu3D_FarahRoom_CAMALT_Balcony.gao` | `3C00144D` | `3C00144C` | `3C00144B` |

Both wrappers reference behavior list `B60024E9` and their respective instance.
The list links definition `B60024E8` and both registration behaviors. These are
therefore named objects capable of entering the registration/selection chain.
This is not evidence that either registration callback has run in the live menu.

Matching instance fields to definition fields by identifier yields the same
serialized values for both objects:

| Runtime field | Value | Source |
| --- | --- | --- |
| `+0x8C` | 1 | Definition default: permits the conditional registration path |
| `+0xA4` | 1 | Definition default: does not trigger the value-2 exclusion |
| `+0x88` | 0 | Definition default |
| `+0xFC` | 0 | Definition default, read by candidate scoring helper `005498A0` |
| `+0x1B4` | 2 | Instance override |

These defaults are not live memory observations. In particular, the previously
traced selection path in `005C0900` requires candidate `+0x88` to be nonzero.
Its initialization remains unresolved. The name CAMALT alone cannot establish
the exclusion mode: its serialized `+0xA4` is 1, not 2. If `+0x1B4` remains 2
at runtime, it does not satisfy the value-4 branch in `005A8980`; runtime changes
and actual selection remain unverified.

## Evidence and next step

Local ignored evidence: `reports/camera-list-population-20261024/` contains five
read-only Ghidra batches and `validate-camera-lists.py` with its JSON result.
The validator independently checks two insertion instruction byte sequences,
three call targets, two native bindings, four GAO-to-body chains and ten selected
field values. This is a real-input static validation, not a runtime regression test.

Inputs, SHA-256:

- `POP.EXE`: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`
- Menu3D decoded container: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`

Next: trace writes to zone `+0x88` and the pose/target fields of these two named
balcony objects. Do not yet identify either as the fixed main-menu camera,
or equate them with Camera02. Original game data and preview defaults are unchanged.
