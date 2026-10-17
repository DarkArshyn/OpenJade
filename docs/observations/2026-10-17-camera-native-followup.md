# Vector motif and native follow-up — 2026-10-17

## Result

The two field-1720 candidates in B60024DE share exactly three token pairs:
`(0,05000025), (1720,14000025), (0,02000960)` at payload offsets
19008 and 19152. Operands are decimal; tag words are hexadecimal.
This repeats a local-vector-like token, the known field candidate and an operation
candidate. Assigning names such as copy, addition or assignment is not justified
without interpreter evidence. The same final tag appears 365, 36 and 27 times
respectively in the three previously selected behavior blocks, with varied contexts.

[REA review](../../references/rea.md) found general native-analysis tooling, not a
Jade opcode specification. No camera transform was changed based on this motif.

## Concrete native leads

A bounded ASCII-string inspection of the two executables in the game root found
AI loader/evaluator diagnostic strings in POP.EXE. PrinceOfPersia.EXE did not
match the selected camera/AI string terms; that does not establish its full role.
POP.EXE is PE32, machine 0x014C, 4280320 bytes, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.

Three strings mentioning AI_ul_CallbackLoadVars, AI_gpst_DynAINodeStack or
AI_gpast_DynAIFunctionTT provide candidate entry points. Mapping their file offsets
through PE sections gives preferred virtual addresses. Searching those address
bytes inside executable sections yields three matches in total. These are **not
validated cross-references or function boundaries**: instruction decoding and
relocation handling are still required.

Local `reports/camera-native-followup-20261017/follow-up.json` records the exact
string offsets, preferred addresses, candidate code locations and vector motifs.
Game bytes and diagnostic strings remain in excluded local reports, not embedded
in documentation as reconstructed source. No game execution or decompilation was
performed. The next evidence needed is the native handler's behavior for the
candidate field-access category and operation 02000960.

## Reproduce

```powershell
python .\src\prepare_camera_native_followup.py <POP.EXE> <tokens.json> <new-output-directory>
python .\tests\test_camera_native_followup.py
```

The script requires the reference executable hash and validates PE32 section
bounds. Two synthetic tests pass for section mapping and malformed/truncated
inputs. Real-data extraction produced three string leads and two vector motifs.
The token JSON is the prior local diagnostic output, not independently decoded
runtime instructions. Executable input is read only and outputs require a new folder.
