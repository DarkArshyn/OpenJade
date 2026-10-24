# Balcony zone pose initialization and unresolved eligibility field

Date: 2026-10-24. Static analysis of the hash-verified executable and
frozen Menu3D container; game inputs remain read-only.

## Verified pose reference

Native binding `B60024E6 -> 005ADE10` belongs to the shared zone behavior list
`B60024E9`. In the mode-2 branch (`+0x1B4 == 2`, serialized in both instances),
it reads object reference `+0x18C`, identifier `3A1A5C4C` (definition tag
`00080028`, instance base tag `0028`). The instance values resolve to:

| Instance | Referenced named object |
| --- | --- |
| `30000D61` | `30000D63`, `Menu3D_FarahRoom_CAM_Balcony.gao` |
| `3C00144B` | `3C00144D`, `Menu3D_FarahRoom_CAMALT_Balcony.gao` |

Both references point to the owning zone itself. Neither is a Camera02
reference. This establishes the serialized input to this initialization path,
not the active main-menu camera or the execution of the behavior.

## Native data flow

For mode 2, `005ADE10`:

1. Reads the referenced object's position through `00475FB0`.
2. Passes that vector through `0049A300`, which calls `0079A900` with the object's
   matrix pointer at object `+0x0C`; stores the result at zone `+0x210..+0x218`.
3. Reads another three-component result through `004778F0`, storing it at
   `+0x1DC..+0x1E4`.
4. Selects behavior `B60024E7` in slot 0 and clears slot 2.

`00475FB0`, in its non-hierarchical branch, refreshes the object then reads the
matrix translation at `+0x30/+0x34/+0x38`. Its other branch walks the hierarchy
and composes matrices. `004778F0` also distinguishes hierarchy/refresh paths
and delegates to `00693F40` in the direct case. The precise vector convention
and `0079A900` operation are not yet established here; do not turn these three
values into assumed Euler angles or apply them directly to the preview.

## Search for zone +0x88 writes

No direct write to `+0x88` appears in the inspected zone bodies `005ADE10`,
`004B3DB0`, `0051FAD0`, `005E60C0`, or the previously inspected registration
bodies. The large serialized body `B60024E5` contains one category-20 operand
`0x88`, at payload offset 5648. Its surrounding tokens were preserved; an
operand occurrence alone is not proof of an assignment. `0300002E` contains
only its terminal token.

A bounded executable byte scan finds stores at the same displacement in other
functions. For example `00517E80` writes 1, whereas `005E8430` writes `0x29`
among many numeric field initializations. Neither has been linked to these
balcony instances. They are not accepted as their writers on offset alone.
The search does not cover all indirect, indexed, interpreter or bulk writes.

Therefore the writer and live value of the balcony zones' `+0x88` remain
unknown. The condition in `005C0900` must not be presented as satisfied by
these objects. Other selection paths and actual callback scheduling also
remain to be established.

## Validation and next step

`reports/balcony-zone-pose-20261024/` contains two read-only Ghidra batches,
`validate-zone-pose.py` and `zone-pose-validation.json`. The validator checks
the native binding, two typed instance self-references and the bounded token
window against frozen input hashes. This is static real-data validation,
not a runtime test. No rendering behavior was changed.

Input SHA-256 values:

- POP.EXE: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`
- Menu3D: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`

Next: decode `0079A900` and `00693F40`, then trace consumers of the initialized
zone fields `+0x210` and `+0x1DC` into the global camera pose. Keep the `+0x88`
eligibility and live-selection questions separate from this established
pose-input chain.
