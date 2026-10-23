# Active camera orientation and field-of-view writers

## Scope and evidence

Static analysis of the local `POP.EXE`, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`,
performed on October 23, 2026 with Ghidra in read-only mode.
Addresses below belong to this executable. Function names are address labels,
not recovered source names. No game resources were modified or executed.

This extends [native matrix calculations](2026-10-22-native-camera-matrices.md).
It identifies writers and data flow, but does not establish the live menu's
selected object, final orientation or final FOV. Renderer defaults are unchanged.

## Camera entry and render block are different structures

Let `W` be the current world/manager, `S = *(W + 0x30) + index * 0xAC`
its camera entry, `C = *(S + 0x90)` its render context and `K = C + 0xCC`
the camera block consumed by the renderer.

| Field | Observed purpose |
| --- | --- |
| `S + 0x00` | Current 0x44-byte source transform |
| `S + 0x44` | Previous transform, saved before full replacement |
| `S + 0x88` | Attached object pointer read by the default update callback |
| `S + 0x8C`, bit 0 | Enable condition checked by the render loop |
| `S + 0x90` | Associated render context |
| `S + 0x94` | Projection angle copied into `K + 0x0C` |
| `S + 0xA8` | Update callback, initialized to `0067BB50` |
| `K + 0x88` | Converted camera pose |
| `K + 0xCC` | Inverse/view matrix |

`0067BF60` allocates/reuses entries, initializes their two transforms from
`00B1AB10`, clears the attached pointer, enables bit 0, installs `0067BB50`,
and assigns the render context from `0080C0C8`. It writes angle 1.0 then copies
entry zero's angle into the new entry. This is initialization behavior, not
evidence for the menu's FOV. It is distinct from the camera-block constructor's
pi/2 default.

## Orientation: attached object to view matrix

The default callback `0067BB50(S)` reads the object pointer at `S + 0x88`.
If nonzero:

1. `00693F20(object, temporary)` copies 17 words (0x44 bytes) from the matrix
   pointed to by `object + 0x0C`.
2. `00693620(S, temporary, ..., 1, 0)` saves the old matrix at `S + 0x44`,
   then copies the complete temporary matrix to `S`. Its last argument is zero,
   so this is the full-transform branch, not the translation-only branch.
3. `006D6CD0(S)` calls `00438830(C + 0xCC, S)` to populate the converted pose,
   then `00437F70(K)` builds its inverse. The axis conversion and subsequent
   helper are described in the preceding matrix report.

Assembly confirms the object read at `0067BB58`, callback copy calls at
`0067BB68` and `0067BB7C`, the source matrix pointer read at `00693F25`,
and the final 17-word copy at `0069367C`.

`006BAD80(W)` calls each non-null camera callback whose render context is
non-null after the preceding world updates. Other callers can invoke it too,
including the FOV setter. A null attached object leaves the transform unchanged
in this callback. Alternative callbacks or other transform writers are not
excluded by this analysis.

## FOV: explicit setter and per-render transfer

`00483CD0(index, angle)` uses world pointer `00AF5650` and updates the selected
entry when its angle differs from the requested value:

| Instruction | Write |
| --- | --- |
| `00483D1E` | Requested angle to `S + 0x94` |
| `00483D5F` | Same angle to `C + 0xD8`, equivalent to `K + 0x0C` |
| `006D6CF2` | Per-render copy of `S + 0x94` to `C + 0xD8` |

After the entry write, the setter invokes its callback. When the context is
non-null it updates projection parameters with `004384C0` and invokes the
projection callback at `C + 0x24`. That callback is `00660690` in the verified
PC setup: it uses `1 / tan(angle / 2)`. The setter performs no degree-to-radian
conversion; the projection consumes radians.

There are multiple native game-logic callers. Two inspected examples are:

- `004B15B0`: under its conditions, obtains a value through `00548F70` and
  passes it to `00483CD0(0, value)`.
- `005BF780`: reads the current angle through `00483FD0(0)`, obtains target
  values through `00548F70` or `00548A70`, and passes an adjusted value to the
  setter. Thus the entry need not retain an asset's initial angle.

`00548F70` reads offset `0x1BC` in the object data reached through
`object + 0x18 -> +0x04 -> +0x44`. `00548A70` reads that same field, or
`+0x184` when `+0x88` is nonzero and `+0x184` is positive. Their callers'
menu relevance and the initialization of those data fields remain unverified.

## Selection at rendering time

`0067AB70` associates the first entry of world `00AF4474` with the render
context, then calls `006D73E0(W, C)`.
The latter iterates entries of size `0xAC`, requiring enabled bit 0 and
`S + 0x90 == C`, stores `S` at `W + 0x34`, then calls `006D6CD0(S)`.
After its loop it also applies entry zero. Consequently a sample taken only
after the loop can miss the entry used for a particular rendering pass.

The same function temporarily replaces the pose from `00B1AB10` for a separate
conditional pass and restores the saved camera block afterward. That temporary
pose must not be mistaken for the scene camera.

## Validation and next bounded investigation

The decompiled field flow was checked against instructions for the FOV writes
and full orientation-copy branch. The existing four synthetic native-camera
math tests remain applicable; they do not validate runtime selection.

Useful future observation points (not performed in this investigation):

- `0067BB58`: resolve the actual attached object and its matrix pointer.
- `0069367C`: observe the matrix entering the camera entry.
- `00483D1E`: record FOV changes and their callers.
- `006D6CF2`: sample the final FOV used for each rendering entry/pass.

The next source-level link is the assignment to `S + 0x88` and its caller in
the menu logic, followed by writes to the relevant controller's angle fields.
The `30000CEF` value 1.2159596681594849 remains a resource candidate: no verified
loader-to-setter link or live observation connects it to the menu's final FOV.
No conclusion that `Camera02` is the active attached object follows yet.

Local ignored evidence: `reports/active-camera-writers-20261023/` contains
selected decompilations, caller references, and instruction exports. Relevant
functions include `0067BF60`, `0067BB50`, `00693F20`, `00693620`, `006BAD80`,
`0067AB70`, `006D73E0`, `006D6CD0`, `00483CD0`, `00548F70` and `00548A70`.
No decompiled game code is added to the tracked source tree.
