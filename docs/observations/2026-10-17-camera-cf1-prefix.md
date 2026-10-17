# CF1 packed-rotation candidates — 2026-10-17

Source: same hash-checked decoded resource as the [CF1 sequence study](2026-10-17-camera-cf1.md).
Record 30000CF1, 624 payload bytes. All offsets below are payload-relative.

## Prefix result

The uint32 at offset 12 is 4. Exactly four 10-byte records fit [22,62):
one uint16 followed by four signed little-endian int16 components.

| Offset | Leading word | Components | Norm |
| --- | --- | --- | ---: |
| 22 | 0x1010 | 0, 0, 0, 32767 | 32767.0000 |
| 32 | 0x0082 | -1157, -449, 4325, 32457 | 32767.4034 |
| 42 | 0x002E | -1314, -538, 4950, 32360 | 32767.1808 |
| 52 | 0x0000 | -1315, -538, 4952, 32359 | 32766.5356 |

Dividing each component by 32767 gives near-unit quaternion candidates, including
an identity candidate first if the last component is the scalar. Signedness and
near-unit norms are directly checked; component order, handedness and rotation
composition are not established. The first leading word 0x1010 is not treated as
a timestamp. No masking or invented time scaling is performed.

## Alternative interpretation of size-like words

Three candidate section spans cover [4,624): [4,62), [62,496), [496,624).
The first uint16 in the payload is 3, consistent with but not proof of three sections.
Their observed word/count pairs are 48/4, 512/32 and 104/2. These yield hypothetical
expanded strides of 12, 16 and 52 bytes. The first two are compatible with expanded
packed-rotation and float-triplet records; the last remains unexplained.
This is a structural hypothesis, not a general section decoder.

**Correction to the earlier timing inference:** the sum of the 32 leading bytes
really is 512, but 512 also equals 32 times 16. It may be a size-like word rather
than a duration. Neither equality establishes timing. Treat that earlier evidence
as ambiguous until the actual encoding is corroborated.

## What this means for Camera02

CF1 plausibly contains both rotation-like and vector-like sequences, strengthening
the motion-track hypothesis. There is still no verified mapping to Camera02's
transform, no frame rate and no interpolation rule. Applying the samples to a
camera now would introduce unverified choices. The inspector deliberately stops
at reproducible raw-field decoding and scaled quaternion candidates.

Next: compare the section headers and leading-word encodings against another
camera-linked sample or an independently understood reader before implementing
playback. Do not infer a decoder from visual plausibility alone.

## Reproduce

```powershell
python .\src\inspect_camera_cf1_prefix.py <decoded.bin> <new-output-directory>
python .\tests\test_camera_cf1_prefix.py
```

Local evidence: `reports/camera-cf1-prefix-20261017/prefix.json`, excluded from Git.
Three tests pass: signed/identity decoding, truncation and rejection of nonunit
candidates. The real four-record sequence passes the extent and norm checks.
No original game data is modified.
