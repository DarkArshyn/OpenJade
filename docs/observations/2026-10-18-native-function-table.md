# Dynamic function table and callers — 2026-10-18

## Scope and evidence

Static inspection of the existing Ghidra 12.1.4 project for PC GOG `POP.EXE`.
SHA-256: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
All addresses below are preferred virtual addresses (image base `00400000`).
No game execution or runtime memory capture was performed. The project was
opened with `-readOnly -noanalysis`.

Local sources: `reports/native-function-table-20261018/evidence/references.txt`
and the assembly/decompiler files named after the functions below. The follow-up
builder references are in `reports/native-function-builder-20261018/evidence/`.
Generated native code remains excluded from Git.

## Resolver callers

Ghidra reports three direct calls to `00463e10`:

| Call instruction | Containing function | Observed context |
| --- | --- | --- |
| `0067a087` | `0067a060` | Guarded by global state, before object-processing loops |
| `00679ded` | `006797b0` | Contains a WOL-loading diagnostic; call follows resource processing |
| `0067767b` | `006775c0` | Contains a loaded-world merge diagnostic; call follows the merge loop |

These contexts support a post-load reference-resolution role. They do not prove
that every possible indirect caller has been recovered, or identify a per-frame
camera update function.

## Construction and lifetime

`00a8d380` is a table of four-byte pointers to dynamic-function descriptors,
not simply a flat array of native handler addresses. `00abc944` is its count.

- `00460040` creates entries. Its text and binary branches check the count
  against `0x1000` (4096), allocate `0x64` bytes per descriptor, store the pointer
  and increment the count. Table writes occur at `0046015e` and `004603cd`.
- The text branch clears 25 four-byte words; the binary branch copies 25 words
  from a temporary record. This corroborates the 100-byte in-memory size, but
  does not alone prove the serialized record size: helper `00424cc0` is unexamined.
- `00462fd0` searches populated entries by the identifier at descriptor offset
  `+0x04`. The loader uses this lookup before adding a new entry.
- `00462f20` releases populated entries, clears pointers and resets the count.
- A second reference query finds a direct call to `00460040` at `00460438`.
  Ghidra does not assign that instruction to a function in the current project;
  its enclosing function and upstream registration path remain unresolved.

Descriptor fields supported by the inspected loader/resolver:

| Offset | Observation |
| --- | --- |
| `+0x00` | Runtime table index written by the loader |
| `+0x04` | Identifier used by lookup |
| `+0x08` | Text loader's model field |
| `+0x0c` | Text loader's file field |
| `+0x10` | Node pointer filled by the resolver and used by the execution consumer |
| `+0x14` | Text loader's parameter count |
| `+0x18` | Text loader's return-type value |
| `+0x1c` onward | Text loader's parameter-type values; complete field bounds unverified |

The resolver processes two pending-node lists. It connects definition nodes to
`+0x10` and rewrites references using the descriptor's index, then clears pending
state. This is stronger evidence for the earlier fixup interpretation.

## Separate execution table

`004a28a0` is an execution consumer of the descriptor table. It reads the signed
16-bit field at node offset `+4`, selects a descriptor, and uses its `+0x10` node
pointer. The inspected assembly performs indirect calls through `007f46fc` with
an eight-byte stride (`004a28f8`, `004a2a14`), selected from a node byte at `+7`.
The called handler returns the next node address. Another branch can invoke a
pointer stored at descriptor `+0x5c` under a global condition.

Thus the descriptor registry and category-dispatch table are distinct. This is
static evidence of an execution path; no handler semantics or camera behavior
have yet been validated. In particular, `0x02000960` remains uninterpreted, and
mapping serialized camera tokens to these in-memory nodes still needs proof.

## Reproduction

First create the analyzed project using the [native setup](../decisions/native-analysis-setup.md).
From the repository root, with the portable installation available:

```powershell
$env:JAVA_HOME = (Resolve-Path '.\reports\native-tools\jdk-21.0.12.1+1').Path
$env:GHIDRA_HEADLESS_MAXMEM = '2G'
$env:GHIDRA_HEADLESS_JAVA_OPTIONS = '-Djava.awt.headless=true'
& .\reports\native-tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat .\reports\native-camera-20261017 CameraResearch -process POP.EXE -readOnly -noanalysis -scriptPath .\tools\ghidra -postScript OpenJadeFunctionTable.java .\reports\function-table-new
```

Output must be a new directory with an existing parent. Default targets are the
resolver, descriptor table and count. To repeat the builder query, append
`00460040` after a different new output path. Optional targets are hexadecimal
virtual addresses. Export is limited to 16 containing functions and 2,000
instructions per function, with truncation reported; decompilation has a
60-second per-function timeout. Unknown function boundaries remain unknown.
These environment settings affect only the current PowerShell process.

## Validation and next step

The default real-data run exported eight functions, all decompiled successfully.
The second run compiled the updated bounded exporter and confirmed the builder
call with an unknown containing function. This is targeted static validation,
not a full test-suite run or proof of complete call-graph recovery.

Next investigate construction and entries of `007f46fc`, then compare a selected
handler's expected node fields against the already extracted camera tokens.
Do not translate recovered implementation into the independent runtime.
