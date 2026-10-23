# Camera-object pointer selection

## Result and scope

The write to camera entry `+0x88` is now identified in the executable.
`004839E0(object, index)` swaps that entry's attached-object pointer and returns
the previous pointer. The store is at `00483A04`. The interpreter wrapper
`00483A10` performs the corresponding store at `00483A8A`.

Source: local `POP.EXE`, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Analysis date: October 23, 2026. Addresses are preferred virtual addresses at
base `00400000`. Ghidra ran with `-readOnly -noanalysis`; selected missing
functions were created temporarily and discarded. No game execution occurred.

This extends [orientation and FOV writers](2026-10-23-active-camera-writers.md).
The selected object's identity in the main menu remains unverified.

## Pointer setter

With world pointer `W = [00AF5650]`, the destination is:

`[W + 0x30] + index * 0xAC + 0x88`

The function reads the old pointer, writes the supplied object and returns the
old value. A null world returns zero without writing. No index bounds check,
matrix update or projection update is present in this small function.

The distinction matters: changing the attachment does not itself copy the new
object's orientation. The already traced callback `0067BB50` subsequently reads
the attachment, obtains its matrix through `00693F20`, and copies it into the
camera entry through `00693620`.

## Two confirmed direct native callers

Let `D = [[00ABC928] + 0x44]`, the field-storage base used by these routines.

| Function / call site | Object passed | Entry index | FOV set immediately before attachment |
| --- | --- | --- | --- |
| `0051DFA0` / `0051DFF6` | `[00ABC930]` | `0` | `D + 0x604` |
| `005A6D10` / `005A6D58` | `[00ABC930]` | value at `D + 0x10` | `D + 0x0C` |

Both calls and their arguments are confirmed in assembly. These routines attach
the current game-logic object; they do not contain a literal Camera02 resource
key or establish its name. The executable-byte search found these two direct
relative calls to `004839E0`, and both were validated as instructions. This is
not an exhaustive proof against indirect calls or other pointer writes.

The FOV setter `00483CD0` invokes the camera callback before these callers swap
the attached pointer. At that instant its callback still sees the previous
attachment. A later callback update can copy the newly attached object's matrix.
This ordering follows the inspected calls; its timing in a running menu has not
been measured.

## Interpreter wrapper and registry

`00483A10` takes the object value from `00ABC934` on entry, before replacing that
global with `00ABC930`. It consumes the entry index from the interpreter stack,
swaps the same `+0x88` pointer and passes the previous object to `0045E170`.
It returns the next eight-byte node address. The incoming `00ABC934` value must
not be automatically equated with the native callers' `00ABC930` argument.

The executable contains the registry pair:

| Address | Value |
| --- | --- |
| `007F60B8` | metadata / serialized identifier `000030D4` |
| `007F60BC` | handler pointer `00483A10` |

It lies at index 701 (`0x2BD`) in the eight-byte table beginning at `007F4AD0`,
whose extent and lookup construction were previously verified in the
[category-dispatch report](2026-10-18-category-dispatch.md).
This gives a bounded resource-language lead, identifier `30D4`. It does not
prove that a matching node executes in the menu or identify the wrapper's
incoming object context.

## Validation and reproduction

The saved Ghidra project did not initially contain these function bodies or
their caller references. A raw executable-byte search for the camera stride
located the setter; relative-call candidates were then checked by disassembling
the containing functions. Empty initial Ghidra reference lists were therefore
not evidence of no callers.

`tools/ghidra/OpenJadeCameraObject.java` exports the four selected functions and
their instructions, checks the executable hash, and records the registry pair.
Use the existing native analysis setup and a new output directory:

```powershell
$env:JAVA_HOME = (Resolve-Path '.\reports\native-tools\jdk-21.0.12.1+1').Path
$env:GHIDRA_HEADLESS_MAXMEM = '2G'
& .\reports\native-tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat .\reports\native-camera-20261017 CameraResearch -process POP.EXE -readOnly -noanalysis -scriptPath .\tools\ghidra -postScript OpenJadeCameraObject.java .\reports\camera-object-new
```

Local ignored evidence: `reports/camera-object-selection-20261023/` contains
the four decompilations, instruction listing and an independent PE-byte check
of both pointer stores, both direct calls and the registry pair. Decompiled
game code remains outside tracked source. No runtime implementation or camera
defaults changed, so no new runtime regression test is claimed.

## Next bounded step

Resolve which behavior/state dispatches `005A6D10` and `0051DFA0`, and identify
the associated object in the extracted menu records. For the interpreter route,
follow the `30D4` call context and incoming `00ABC934` value. Then connect that
object to its stored transform and FOV fields. The static Camera02 transform
and resource `30000CEF` remain candidates until this association is established.
