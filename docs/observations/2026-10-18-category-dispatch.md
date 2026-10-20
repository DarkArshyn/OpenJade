# Category dispatch and vector-copy motif — 2026-10-18

## Scope

Static evidence from PC GOG `POP.EXE`, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Addresses are preferred VAs at base `00400000`. No game execution occurred.
The existing project was processed with `-readOnly -noanalysis`; missing selected
function boundaries were created temporarily and discarded on close.

## Serialized identifiers differ from runtime indices

`00462b10` builds a lookup at `00a91380` from five tables. Its first loop has
22 entries starting at `007f46f8`, with an eight-byte stride: metadata precedes
the handler pointer by four bytes. The pointer-column base is `007f46fc`.
The remaining loops cover 26, 75, 1173 and 27 entries, starting at `007f47a8`,
`007f4878`, `007f4ad0` and `007f6f78` respectively.

`0045e910` processes eight-byte nodes. For applicable categories it replaces the
16-bit parameter at `+4` through the lookup, then remaps the category byte at
`+7`. It stops at serialized category `0x1f` before remapping that terminator.
Several categories explicitly bypass parameter remapping. These exceptions mean
that blindly remapping every field would be incorrect.

| Serialized category | Runtime index | Handler | Observed role |
| --- | --- | --- | --- |
| `02` | `01` | `004a2020` | Indirect operation dispatch via `007f487c` |
| `05` | `04` | `004a25d0` | Push typed value/address from local storage plus operand offset |
| `14` | `08` | `004a2770` | Push typed value/address from current object field storage plus operand offset |
| `1f` | Table entry `15` | `0049ee40` | Loader stops before remapping; runtime loops also check raw `1f` |

The earlier exploratory 32-slot dump crossed into the adjacent type table. The
final exporter uses the verified 22-entry category extent and preceding metadata.
Only the final evidence should be used for identifier-to-handler interpretation.

## Type and operation corroboration

The type record for serialized `0x25` at index 3 of `007f47a8` has metadata
`000c0025` and handler `004a1f80`. That handler copies three 32-bit words.
This supports a 12-byte value, consistent with the earlier triplet interpretation;
it does not by itself establish floating-point arithmetic semantics.

Serialized operation `0x960` maps to index `0x3a` in `007f4878`, whose handler
is `004a1910`. The category-02 dispatch uses the remapped parameter to reach it.

`00460be0` pushes a typed value into 32-byte value-stack slots and records its
source address in a separate eight-byte descriptor stack. `004a1910` consumes
two stack entries and copies three 32-bit words from the second pushed value
to the address recorded for the first. Assembly corroborates the destination
stores at `004a1963`, `004a1968`, and `004a1976`; it advances the node by eight.
This supports a three-word assignment/copy interpretation for this handler.
No original implementation is included in project source.

## Application to the existing camera motif

The two previously observed B60024DE sequences, starting at payload offsets
19008 and 19152, contain:

| Operand | Serialized tag | Evidence-backed interpretation |
| ---: | --- | --- |
| 0 | `05000025` | Local typed value/address at offset 0 |
| 1720 | `14000025` | Current object's typed field value/address at offset 1720 |
| 0 | `02000960` | Three-word copy to the first operand's address |

If this sequence executes through the inspected loader and interpreter, it copies
the field at offset 1720 into the local at offset 0. It does not write that local
back to the object field. This strengthens the local-copy interpretation but does
not prove execution, identify the live current object, establish the live field
value, or show that the value becomes a camera translation. Those remain separate
questions. The archived instance triplet `(0,0,8)` must not be applied to a camera
transform solely on this evidence.

## Validation and local evidence

Final output: `reports/native-category-vector-20261018/evidence/`. Thirteen
functions exported and decompiled successfully. Indirect-dispatch decompiler
warnings remain; their target calculations were checked against assembly.
`validation.json` records an independent PE-byte check of four category records,
one type record, one operation record, and both previously exported motifs.
This is targeted real-data validation, not runtime testing or a full suite.

The initial exploratory outputs in `native-category-table`, `native-category-handlers`
and `native-category-mapping` report directories are retained locally for provenance.
All are dated `20261018` and excluded from Git. The original executable hash was
verified before analysis and during independent validation.

## Reproduce

With the [portable native tools](../decisions/native-analysis-setup.md), run in a
PowerShell session from the repository root:

```powershell
$env:JAVA_HOME = (Resolve-Path '.\reports\native-tools\jdk-21.0.12.1+1').Path
$env:GHIDRA_HEADLESS_MAXMEM = '2G'
$env:GHIDRA_HEADLESS_JAVA_OPTIONS = '-Djava.awt.headless=true'
& .\reports\native-tools\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat .\reports\native-camera-20261017 CameraResearch -process POP.EXE -readOnly -noanalysis -scriptPath .\tools\ghidra -postScript OpenJadeCategoryTable.java .\reports\category-new
```

The output path must be new. Keep `-readOnly`: temporary disassembly/function
creation exists only to inspect selected indirect targets. Export remains bounded
to 16 functions, 2,000 instructions per function and 60 seconds per decompilation.
The script validates the executable hash and base before inspecting fixed targets.

Next: follow the consumers of local offset 0 after the two motifs, and identify
which subsequent operations could use the triplet in camera positioning. Preserve
unknown control flow and do not infer that a static sequence necessarily runs.
