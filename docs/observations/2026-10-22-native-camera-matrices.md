# Native camera view and projection calculations

## Scope

Static analysis of the hash-checked POP.EXE, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
This identifies calculations and field flow, not the camera state selected by
the main menu at a particular frame. No game files or default preview settings
were changed.

## Render-context flow

`00425F30` initializes a camera block at render-context offset `0xCC` through
`004382B0`. Its initial angle is `0x3FC90FDB` (approximately pi/2 radians),
depth fields start at 1 and 500000. These are constructor defaults, not proof
of the values used by the menu.

`00425DB0` updates the camera projection parameters through `004384C0`, calls
the callback at render-context `+0x24` with the camera block, then updates its
inverse through `00437F70`. `00425CF0` installs **00660690** in that callback.
This connects the generic camera block to the PC graphics projection routine.

## View calculation

`00438830` is a wrapper that adds `0x88` to its destination before jumping to
`00438790`. This argument adjustment is missing from its short decompilation;
the saved assembly instructions establish it.

`00438790` copies the supplied orientation via `00438160`, copies translation,
swaps its second and third basis rows and changes signs. If the incoming rows
are `B0, B1, B2`, the resulting rows before helper processing are:

```text
-B0, -B2, -B1
```

It then calls `0079BA70`, which checks matrix properties and may call another
basis-processing helper. The small Python reconstruction exposes the axis
conversion separately and does not reproduce all that helper's behavior.
Do not apply this conversion indiscriminately to an already converted matrix.

`00437F70` builds the rigid inverse of the camera-block transform at `+0x88`
into `+0xCC`: `0079AD50` transposes its 3x3 basis, then `0079A080` transforms
the negated camera position by that transposed basis. For row-vector notation:

```text
V.rotation = R.transpose()
V.translation = -position * R.transpose()
```

This is a verified camera-block operation. The path selecting/populating that
block from the menu's Camera02 GAO still needs to be established. The signs and
axis conversion must not be combined with the current diagnostic renderer's
conventions without tracing the complete path.

## Projection coefficients

`00660690` reads angle `a` at camera-block `+0x0C` and depth fields `d0`, `d1`
at `+4`, `+8`. Constant `007A8E5C` is 2.0 and `007A5934` is 1.0. The math
function at `00729824` contains the x87 **FPTAN** instruction, confirming:

```text
c = 1 / tan(a / 2)
```

The angle is used directly as a radian input. For context `+0xC8` between 1 and
6, ratio `r` is global configuration field `+0x94 / +0x90`; otherwise it uses
context `+0xB4`. The branch depends on bit 4 of context `+0xAC`:

| Coefficient | Bit clear | Bit set |
| --- | --- | --- |
| P00 | c | c * r |
| P11 | -c / r | -c |

The remaining nonzero coefficients in the 16-float output at `00AEBFE0` are:

```text
P22 = (d0 + d1) / (d1 - d0)
P23 = 1
P32 = float32(-0.05)
P33 = 0
```

The negative vertical coefficient and fixed depth term are observed, not
replaced with a textbook perspective matrix. In particular, the names
near/far alone would not explain the fixed `-0.05` term. Its wider depth-state
implications require further investigation.

Conditionally, if `r=600/800` and bit 4 is clear, the stored candidate angle
`1.215959668` would correspond to a vertical angle of about 55.12 degrees.
The link from resource `30000CEF` to this runtime angle field is **not yet
proved**, so this is not a recovered main-menu FOV. The current fit remains
independent evidence, not validation of that candidate.

## Matrix upload

`00668620` copies the projection into graphics-context `+0x60`, prepares a
separate matrix block and updates the combined matrix. `006685B0` similarly
copies the other input matrix into `+0x20`. Their arithmetic helpers are
runtime-dispatched library routines; their exact selected implementations
were not resolved in this step.

`00667B00` sends matrix-related blocks through device vtable offset `0x178`,
including 12 vectors from register 0 and four from register `0x15`. Generated
shader code in `0066E630` uses an `m4x4` operation starting at constant 0 for
transformed positions. This supplies a concrete downstream path to investigate;
the exact complete model/view/projection composition remains to be confirmed.

## Independent implementation and validation

`src/menu_native_camera_math.py` implements the observed projection coefficients,
the separate axis conversion and rigid inverse, with explicit caller inputs.
It is not integrated into the default renderer. Four synthetic tests verify
rigid inverse geometry, the axis mapping, perspective edge/depth coefficients,
and rejection of invalid inputs:

```powershell
python -B .\tests\test_native_camera_math.py
```

Local ignored evidence: `reports/native-camera-matrices-20261022/`, including
decompilations, reference listings and assembly excerpts. The two new Ghidra
scripts export a bounded existing-function range and targeted instructions;
they enforce the executable hash and are run with `-readOnly -noanalysis`.

Next: trace the active camera block's angle/orientation writers and resolve the
runtime-dispatched matrix arithmetic. A live matrix capture would additionally
establish which state is actually selected on the main menu.
