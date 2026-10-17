# Camera behavior token boundaries — 2026-10-17

Source SHA-256: `68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`.
This follows the [field-use candidates](2026-10-17-global-camera-field-uses.md).

## Structural result

In the three selected `.ofc` records, the uint32 at payload offset 4 delimits an
area starting at offset 8. Its length is divisible by eight. Reading that area
as pairs of little-endian uint32 words aligns all six previously found field
references. We call these pairs tokens; this does not prove one token equals
one executable instruction. The first header word remains opaque.

| Record | Declared area bytes | Tokens | Preserved trailing bytes |
| --- | ---: | ---: | ---: |
| B60024DE | 114640 | 14330 | 550 |
| B6002512 | 5528 | 691 | 29 |
| 080009C9 | 6624 | 828 | 38 |

The first token word is retained as a candidate operand; the second is split
into a high-byte category and a low-24-bit value, without assigning opcode names.
Field candidates have category 0x14 and low values 0x22 or 0x25, agreeing with
the definition's float/triplet type. All three areas end with a category 0x1F
token; its execution meaning is unknown.

## Cross-block corroboration

At field offset 1716, the maximal exact run around the reference spans 12 tokens
(96 bytes): B6002512 payload [3712,3808) equals 080009C9 [5720,5816).
At field offset 1508, the corresponding run is two tokens (16 bytes), at
[5072,5088) and [6256,6272). These comparisons use whole token pairs.
The longer shared sequence provides evidence of reused encoded behavior;
it does not establish that the blocks execute in the same circumstances.

For the vector candidate, B60024DE contains aligned pairs (1720,0x14000025)
at offsets 19016 and 19160. Nearby categories include 0x05 and 0x02, but reads,
writes, calls and operand-stack conventions are not decoded. Applying (0,0,8)
as a camera translation is still unsupported.

## Tool and checks

```powershell
python .\src\inspect_camera_behavior_tokens.py <CameraAndGlobal-decoded.bin> <new-output-directory>
python .\tests\test_camera_behavior_tokens.py
```

Local evidence: `reports/camera-behavior-tokens-20261017/tokens.json` includes
all tokens, raw tail bytes, category counts, six field candidates and shared runs.
The tool checks the frozen source hash, unique selected keys and byte bounds.
Three synthetic tests pass: token/tail separation, malformed lengths and maximal
shared-run boundaries. Real-data checks validate all three extents and comparison
anchors. No execution, runtime semantics or original camera behavior is claimed.

Next: corroborate numeric category meanings and expression boundaries using
additional repeated patterns or an independently understood format. The current
output is a structural token listing, not a behavior disassembler.
