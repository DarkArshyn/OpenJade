# Vector descriptors and downstream consumers — 2026-10-18

## Scope

Targeted continuation of [local vector flow](2026-10-18-local-vector-flow.md).
The same PC GOG executable hash and CameraAndGlobal resource hash apply. No game
execution occurred. Native addresses below are preferred virtual addresses.

## Dynamic-function descriptors

Record `08000338` contains 49 compact descriptors: 4 + 49 * 88 = 4316 bytes.
The native reader `00424cc0`, together with `00420660`, supports this compact
form: four words, two more words and sixteen parameter-type words (88 bytes).
The runtime descriptor reserves additional fields and is 100 bytes; serialized
and runtime layouts must not be conflated. Other loader modes skip additional
fields and are not supported by the new reader.

| Identifier | Record payload offset | Stored index | Model | File | Parameters | Return |
| --- | ---: | ---: | --- | --- | --- | --- |
| `5b82` | 1500 | 614 | `263c` | `005d` | None | `25` |
| `5b83` | 2380 | 624 | `263c` | `005d` | One `25` | `25` |

Identifiers/model/file/types are hexadecimal. Stored indices and offsets are
decimal. Type 25 is the three-word value previously corroborated natively.
Stored indices are not guaranteed to equal runtime indices after deduplication.
The model/file values are retained as identifiers: their conversion into resource
keys is unresolved. These descriptors identify signatures, not implementations.

The link list B60024E2 leads to 27 OFC records and six TTT keys. All 27 OFC
records were inspected for definition tokens `1c005b82` and `1c005b83`; neither
was found. Four TTT payloads were inspected. Two keys, 08001E29 and 057CC827,
have conflicting duplicate payloads and were explicitly left unresolved.
Thus this is a bounded negative finding, not proof that the functions are absent
from the game. The complete bodies of 5b82 and 5b83 remain unidentified.

## What happens after addition in 080009C9

Offsets are relative to this record payload:

1. At 1000, operation 0961 adds the result of 5755 into local vector 24.
2. At 1008, local 24 is pushed as the destination for a later assignment.
   Field 1040 selects object context via 0806 at 1024.
3. The call to 5b83 at 1032 is followed by local 24 at 1040 and 0836 at 1048,
   supplying the vector argument. The argument terminator is at 1056.
4. Operation 0837 retrieves the result at 1064; 0960 assigns it to local 24 at 1072.
5. Locals 48 and 24 feed 0965 at 1104. The result is assigned to local 124 at
   1112: **local124 = local48 - local24**, component by component.
6. A later selected expression compares local 48 and local 24 using 096b at
   1216. Later still, 0965 at 1256 subtracts an object-derived triplet from local 24.
   Intervening conditional paths mean these later operations are not asserted
   to execute on every visit.

The dynamic call machinery examined earlier supports the argument/return
interpretation, and the newly found 5b83 signature agrees with one vector argument
and a vector result. Without its body, no name such as rotate/transform/clamp is
assigned to 5b83.

## Native corroboration

- 0965 maps to `004a1430`: subtracts the second stacked float triplet from the
  first. Assembly includes three floating-point subtraction instructions.
- 096b maps to `0049fec0`: produces false when all three components compare equal,
  true otherwise. This is a component-wise floating-point inequality result.
- Category-03 identifier 1fa5 maps to `004760e0`, which calls `00475fb0` and pushes
  a three-component object-derived value.
- In one branch, `00475fb0` calls `00695120`, then reads offsets 30/34/38 (hex)
  from the structure referenced at object offset 0c. Another branch traverses
  object relationships and calls matrix-related helpers. This motivates a
  transform/position investigation, but the update, coordinate space, object
  identity and matrix helper semantics have not been verified here.

These results support vector arithmetic and object-associated data flow. They do
not establish a camera view matrix, world-space position, rendered framing or a
correct reconstructed scene. No original implementation is copied into the project.

## Tools, validation and reproduction

```powershell
python .\src\inspect_camera_function_descriptors.py .\reports\camera-global-comparison\decoded\decoded.bin .\reports\camera-function-descriptors-new
python .\tests\test_camera_function_descriptors.py
```

The reader checks the frozen source hash, compact extents and parameter bounds;
retains all descriptor words; reports duplicate keys; and refuses to choose among
conflicting linked payloads. It only follows the selected camera link list.
Three synthetic tests cover compact extent errors, fields/duplicate IDs and the
16-parameter bound. The real-data run found two descriptors and no matching
function-definition tokens in the 27 linked OFC records.

Native exporter: `tools/ghidra/OpenJadeVectorConsumers.java`. Use the previous
headless command with this script and a new output directory, retaining
`-readOnly -noanalysis`. Seven functions were exported/decompiled in the final
run. Evidence remains in `reports/native-vector-descriptors-20261018/evidence/`;
parsed descriptors are in `reports/camera-function-descriptors-20261018/`.
The first exploratory native run remains in `native-vector-consumers-20261018`.

Next: resolve model/file identifiers 263c/005d through the loading path to locate
5b82 and 5b83, and verify the transform update behind 00695120. Neither unknown
is replaced by a guessed implementation.
