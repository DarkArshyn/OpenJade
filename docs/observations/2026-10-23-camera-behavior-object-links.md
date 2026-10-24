# Native camera callers, behaviors and objects

## Result

One of the two native camera-selection callers now has a verified static object
chain: `0051DFA0` is bound to behavior resource `3200043D`, which belongs to
`Camera.gao` (`CC000403`) in the decoded CameraAndGlobal container. Its serialized
body independently corroborates FOV field `0x604` and camera-entry index zero.

The other caller, `005A6D10`, is bound to `03002045`. That record is absent from
both selected containers (Menu3D and CameraAndGlobal), so no menu-object identity
is assigned to this second caller.

These are static links, not proof of the active state during a captured menu.
They do not establish that Camera02 itself is attached to the renderer.

## Sources and reproducible scope

Analysis performed October 23, 2026, using the local executable and two
already decoded resources, all read-only:

| Input | SHA-256 |
| --- | --- |
| POP.EXE | `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9` |
| Menu3D | `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb` |
| CameraAndGlobal | `68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582` |

This extends [camera-object selection](2026-10-23-camera-object-selection.md).
Ghidra function labels denote addresses, not recovered original names.

## Native binding table: key first, pointer second

`0045EEF0` loads a behavior resource. When `007F28B8` is nonzero, it obtains the
current load key through `004207D0`, compares it with entries at
`007F28C0 + index * 8`, and stores the paired pointer from
`007F28C4 + index * 8` at loaded-behavior offset `+0x10`.
`00462AB0` returns the bound `0x3C7` (967 entries).

| Key address | Resource key | Pointer address | Native function |
| --- | --- | --- | --- |
| `007F3FB8` | `3200043D` | `007F3FBC` | `0051DFA0` |
| `007F3F30` | `03002045` | `007F3F34` | `005A6D10` |
| `007F3F38` | `B60024F7` | `007F3F3C` | `00605670` |

The neighboring key `B60024F7` must not be paired with the preceding pointer
`005A6D10`. The loader establishes the column order, avoiding an off-by-one
association. Binding a native implementation is conditional on the native-mode
flag; no live branch selection was observed.

## Global camera activation chain

The checked CameraAndGlobal chain is:

`CC000403 Camera.gao -> 057CC738 -> B60024E2 -> 3200043D -> 0051DFA0`

- The GAO references wrapper `057CC738` at payload offset 197.
- The wrapper is exactly the pair `B60024E2 / 057CC737` (behavior list / instance).
- The typed list includes `3200043D .ofc` and definition `B60024E1 .ova`.
- The binding table associates `3200043D` with the native caller `0051DFA0`.

The 148-byte OFC payload contains the following motif:

| Payload offset | Operand | Tag | Corroborated role |
| --- | --- | --- | --- |
| 32 | 0 | `01000021` | Entry index zero |
| 40 | `0x604` | `14000022` | Object float field |
| 48 | 0 | `030030D9` | FOV operation, matching native `00483CD0` call |
| 56 | 0 | `01000021` | Entry index zero |
| 64 | 0 | `030030D4` | Attachment operation, matching native `004839E0` call |

The native implementation passes current logic object `00ABC930` to the
attachment setter. This is a behavior association with `Camera.gao`, not an
assertion that this native state necessarily runs at menu startup.

Definition field `0x604` has identifier `2B90B3C7` and stored float 1.0.
The small instance block does not explicitly provide that offset. This is a
definition value only: initialization, later changes and the live menu FOV are
not established. Do not replace the preview camera with a one-radian FOV.

## Menu camera manager and cross-container connection

The independently checked Menu3D chain is:

`B60024ED Cam_Manager.gao -> B60024EF -> B60024E4 -> B60024F7 -> 00605670`

The GAO reference is at payload offset 160. Its wrapper is exactly
`B60024E4 / B60024EE`. The list contains several OFC states, including
`B60024F7`, `B60024F8`, `320002ED` and `32000455`.

`00605670` processes queued data, checks a `0x72` discriminator and calls
`004B1010` under its conditions. That helper resolves object key `CC000403`
through `0045E800(0x28, CC000403)` and has a conditional call to
`005C02E0` with that resolved object. This establishes a reference from the
menu manager's native logic to the global `Camera.gao` object. The detailed
effect of `005C02E0` and the startup condition selecting that path are not yet
verified; this is not a demonstrated direct call to activation state `3200043D`.

The manager's `320002ED` state is bound to `00616630`, which also calls the FOV
setter using a value obtained through `00548F70` from another selected object.
This further cautions against treating a resource default as the final FOV.

## Validation and next step

`src/link_menu_camera_behaviors.py` checks all three hashes, the bounded native
table, three bindings, both typed object chains, and the activation motif. It
retains selected record multiplicity and rejects ambiguous records/bindings.
Three synthetic tests cover column order, truncated/duplicate bindings and
duplicate resource records. The real-data run passed all selected checks.

```powershell
python -B .\tests\test_menu_camera_behaviors.py
python -B .\src\link_menu_camera_behaviors.py .\game\TSoT-GOG\POP.EXE .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\camera-global-comparison\decoded\decoded.bin .\reports\camera-behavior-new
```

Local ignored evidence: `reports/camera-behavior-links-20261023/` contains
`links.json` and selected native exports. The Ghidra exports can be repeated
with the existing `OpenJadeFog.java` helper, selecting `0045EEF0`, `00462AB0`,
`004207D0`, `00605670`, `004B1010` and `00616630` in read-only mode.

Next: follow `005C02E0` and the global camera's activation/state transition,
then identify the selected pose source supplied to `Camera.gao`. Camera02 may
be such a source, but that relationship remains unverified. No camera defaults
or game resources changed, and no general archive-wide scan was performed.
