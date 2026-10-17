# Native camera entry points — 2026-10-17

## Scope and reproducibility

Static Ghidra 12.1.4 analysis of the PC GOG `POP.EXE`, x86 little-endian,
preferred image base `00400000`. Input SHA-256: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
The original executable was not run. Analysis used a verified local copy.
See [setup and reproduction command](../decisions/native-analysis-setup.md).

## Confirmed references

Addresses below are preferred virtual addresses, not file offsets.

| Diagnostic string address | Referencing instruction | Enclosing function |
| --- | --- | --- |
| `007a9438` | `0045fdf1` | `0045f2a0` |
| `007a97e8` | `00463e8f` | `00463e10` |
| `007a9844` | `00463e52` | `00463e10` |

All three references are decoded PUSH instructions. The earlier byte-search
matches lie one byte after these instruction starts, in the immediate operands.
Both enclosing functions were decompiled successfully. These are confirmed
references to the diagnostics, not yet confirmed camera execution entry points.

## Interpretation and limits

- `0045f2a0` contains the unsupported-variable-type diagnostic. Its decompiler
  output includes a length divided by twelve and iteration over three-word
  records, supporting investigation as a variable-descriptor loader.
- `00463e10` reads a signed 16-bit field at node offset four, accesses a table
  at `00a8d380`, checks references and clears temporary stack state. This supports
  a reference-resolution/fixup interpretation; it does not establish that this
  function dispatches runtime camera instructions.
- Function names shown by Ghidra are generated labels. Decompiled types and
  control flow remain analysis aids, not independently verified source.
- No meaning is assigned here to `0x02000960`, and no camera movement or native
  execution behavior has been reproduced by this experiment.

## Validation and local evidence

The real-data run completed automatic analysis in approximately 146 seconds,
exported the three references and two functions, and saved the Ghidra project.
The original and copied executable hashes matched after analysis.
The Java export script compiled and ran in Ghidra. The reusable PowerShell
wrapper was syntax-checked with Windows PowerShell 5.1; the initial real-data
run used an equivalent local launcher, not an end-to-end run of that wrapper.

Local evidence is under `reports/native-camera-20261017/`: `analysis.log`,
`script.log`, `evidence/entry-points.txt`, bounded assembly listings, decompiler
output and the project database. These generated files remain excluded from Git.
Warnings included unresolved BINKW32/EAX libraries, a resource-image issue and
a decompiler issue in another function. Completion is not proof of complete
executable analysis or correct recovered types.

Next: inspect callers and table construction around `00463e10`, then identify
an actual runtime consumer before assigning semantics to the resource tokens.
Keep native code evidence local; publish observations and independently written
tools, not recovered game implementation.
