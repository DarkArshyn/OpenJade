# Local vector flow and callers — 2026-10-18

## Evidence scope

Follow-up to [category dispatch](2026-10-18-category-dispatch.md). Static analysis
of PC GOG POP.EXE, SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`,
and the three previously selected token blocks. Payload offsets below belong to
B60024DE unless otherwise specified; native addresses are preferred VAs.
No runtime execution, live object identity or actual branch outcome is asserted.

## The two copies are alternative paths

The enclosing definition token is `1c005755` at 18904. Its selected flow is:

| Payload offset | Observed operation | Consequence |
| ---: | --- | --- |
| 19000 | `0900`, operand 5 | False condition branches to 19040; otherwise 19008 |
| 19008–19024 | Local 0, object field 1720, `0960` | Copies the object field into local 0 |
| 19032 | `08fc`, operand 18 | Unconditional jump to 19176 |
| 19040–19088 | Local 0; context from field 1040; call `5b82`; retrieve result; `0960` | Assigns the dynamic call result to local 0 |
| 19096–19136 | Local 0; three zero constants; `1770`; `096a` | Constructs a zero triplet and compares all three floating-point components |
| 19144 | `0900`, operand 4 | Nonzero comparison result falls through; zero comparison result branches to 19176 |
| 19152–19168 | Local 0, object field 1720, `0960` | Replaces the zero result with the field value |
| 19176–19192 | Local 12, local 0, `0960` | Copies the selected vector to local 12 |
| 19200–19216 | Local 12, `0836`, `0834` | Transfers the value to the return-value stack and exits the function path |

Branch targets use **current offset + operand × 8**, not next offset plus displacement.
For example, 19032 + 18 × 8 = 19176. `0900` consumes a condition and jumps when
zero. The condition before 19000 was not fully decoded here: no branch is assumed
taken. The two field copies must not be interpreted as two consecutive assignments.

Interpretation: this function selects either the existing field vector or a
nonzero vector obtained from another dynamic function, then returns it. Whether
that vector represents a position, offset or another quantity remains unknown.

## Native operation evidence

| Serialized ID | Native handler | Supported interpretation |
| --- | --- | --- |
| `08fc` | `0049ee70` | Unconditional relative node jump |
| `0900` | `0049f440` | Pop condition; relative jump if zero |
| `1770` (category 03) | `0049ea40` | Construct a float triplet from three scalar operands |
| `096a` | `0049fe10` | Equality test of all three float components |
| `0836` | `0049f070` | Pop typed value/address, copy through `0049ee80` to the return stack |
| `0837` | `0049f0d0` | Retrieve typed return value through `0049eee0`, push evaluation value |
| `0834` | `0049ed90` | Exit dynamic-function body or terminate the current evaluation path |
| `0806` | `0049ef50` | Update object-related evaluation context from a stacked object reference |
| `0961` | `004a1a10` | Add three float components to the first operand's referenced destination |

Return helpers `0049ee80` and `0049eee0` use a distinct typed stack. This supports
calling 0836/0837 return-value transfer operations in this observed call sequence.
No original implementation is added to the project; decompiler files stay local.

## Consumers in the selected resources

Two call tokens for `5755` were found among the three already indexed blocks:

- B6002512 at 1336: destination local 112 is pushed at 1328; after the call,
  0837 retrieves the result at 1352 and 0960 assigns it at 1360.
- 080009C9 at 976: destination local 24 is pushed at 968; 0837 retrieves the
  result at 992 and 0961 adds it to that local at 1000.

This is a bounded search, not a claim that these are the only callers in the game.
The local offsets belong to different function frames and must not be equated.
The definition for dynamic function `5b82` was not present in the three selected
blocks. Its calculation remains unresolved. The runtime descriptor lookup has
not been validated against a live process.

## Validation and reproduction

Final native evidence: `reports/native-local-vector-callers-20261018/evidence/`.
Fifteen functions were exported and decompiled successfully, including the dynamic
call handler and four return helpers. `validation.json` checks three branch targets,
ten definition/operation anchors, the join-point copy and the two callers against
the existing token JSON. The executable hash remains unchanged.
Earlier intermediate reports under `native-local-vector` and
`native-local-vector-return` (same date suffix) are retained locally.

Use the [native setup](../decisions/native-analysis-setup.md) and the same headless
command as [category dispatch](2026-10-18-category-dispatch.md#reproduce), replacing
`OpenJadeCategoryTable.java` with `OpenJadeLocalVectorUses.java` and choosing a new
report directory. Keep `-readOnly -noanalysis`: selected missing function boundaries
are created temporarily and discarded. Export limits remain 16 functions, 2,000
instructions each and 60 seconds per decompilation. This is static evidence,
not a test of game execution or proof of complete control-flow recovery.

Next: locate the resource defining `5b82` through the dynamic-function descriptors,
and follow local 24 in 080009C9 to determine how the resulting sum is consumed.
Neither the field fallback nor the addition alone establishes a camera transform.
