# Bounds gate: scoped reference search — 2026-10-20

Field 276 (identifier C4E1F69A) still has no established runtime writer.
This step narrows two leads without treating a negative search as proof of
disabled bounding.

## Identifier inventory

A payload-only byte search of the two frozen Menu3D and CameraAndGlobal resources
finds one occurrence: Menu3D record B60024E8, payload offset 1220.
The existing field-table reader confirms that this identifier belongs to the
descriptor at value offset 276, count 1, tag 0x000A0021, stored value zero.
No additional occurrence exists in CameraAndGlobal.

This is an identifier inventory, not a general write scan. The already observed
category-14 accesses encode an offset, not this identifier. Indirect, native and
other-resource accesses are not excluded. The previous eight-block behavior
inspection remains the evidence for the absence of a direct writer in that scope.

## Operation 1007

In B60024E5, payload offset 5960 contains constant operand 75 with tag 0x01000026.
Offset 5968 invokes builtin 1007, before the field-276 read at 5976.
The native builtin table resolves 1007 to 00467850.

Assembly confirms that this wrapper calls 0045e260 and advances one token.
The helper consumes one evaluator-stack value, dispatches through a type handler,
and can resolve a reference through two lookup helpers. Its returned pointer is
not used by the wrapper. Neither inspected function contains a direct assignment
to object field 276. The type handler and lookup helpers were not exhaustively
traced, so indirect effects are not ruled out. No diagnostic text or symbolic
builtin name is inferred from this alone.

Evidence is local and excluded from Git:
`reports/native-bounds-gate-helper-20261020/evidence/`, including assembly and
decompilation for 00467850 and 0045e260. The Ghidra run used the existing frozen
PC GOG project with `-readOnly -noanalysis`; temporary analysis changes were
discarded. `tools/ghidra/OpenJadeBoundsGate.java` reproduces the selected export
using the established headless workflow and a fresh output directory.

## Validation and next step

```powershell
python .\src\inspect_bounds_gate_references.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\camera-global-comparison\decoded\decoded.bin .\reports\bounds-gate-new.json
python .\tests\test_bounds_gate_references.py
```

Both input hashes are checked. Two synthetic tests cover payload/header separation,
unaligned and repeated matches, offsets and truncated records. The real-data run
finds one and zero hits respectively. No game resources or viewer behavior change.

The next useful target is instance creation: locate the native path that copies
definition defaults and applies instance overrides, then determine whether field
276 can change before callbacks run. Its archived zero is not yet a verified
runtime value.
