# Camera comparison and global-resource lead — 2026-10-17

## Scope and negative results

Five explicitly selected decoded resources were inventoried, not the entire game.
Menu3D and the retained antichambre sample were already decoded. MenuBoot,
MenuCredits and CameraAndGlobal were selected by names in the existing BIG index
and extracted using Extract-BIG.ps1, then decoded using Expand-POPLzo.ps1.
Stored bytes, decoded bytes, trailing bytes and manifests are retained locally.

| Resource | Decoded bytes | Records | Result |
| --- | ---: | ---: | --- |
| Menu3D FF000CB9 | 4469220 | 633 | Camera02 and CF1; no second same-signature block |
| Antichambre FF024957 | 1296307 | 240 | No camera-named GAO found |
| MenuBoot FF0B5CBA | 1141254 | 48 | Menu_MessageBox and Menu_Boot GAOs |
| MenuCredits FF0BA846 | 1134515 | 46 | MenuCredits GAO |
| CameraAndGlobal FF0C03FD | 306943 | 66 | Camera.gao and Global.gao |

The heuristic signature requires payload length >=16, bytes [6,8) equal FFFF,
and initial uint16 in 1..9. It is only a candidate filter. The short matches
0F0033A7 (antichambre) and 55000012 (global) do not validate the CF1 layout.
No second complete CF1 encoding was established. Absence under this filter does
not exclude other camera or motion encodings.

## Stronger global-camera lead

The decoded Menu3D WOL contains pair `CC0003FD, .wow` at file offset 116
(payload offset 104). CameraAndGlobal's first record key is CC0003FD.
This is a direct key/type match, supporting a dependency relationship;
runtime loading order and camera activation are not established.

Camera.gao has key CC000403 and candidate identity basis with position (1,0,0).
Its payload references CC000404 at offset 133, 057CC738 at 197 and 55000013 at 201.
The latter records are not interpreted as a second CF1 track.
CC000404 is a 24-byte parameter block, like Camera02's 30000CEF:

| Payload offset | Camera02 word/value | Global camera word/value |
| --- | --- | --- |
| 0,4,8 (uint32) | 6,0,1 | 6,0,1 |
| 12 (raw hex) | 00000000 | 0000803f |
| 16 (float32) | 1000 | 2000000 |
| 20 (float32) | 1.215959668 | 1 |

Field semantics, including projection/clipping meanings, remain unknown.
The presence of this distinct camera means Camera02 should not be assumed to
be the active menu view. It does not prove that the global camera is active.
The CameraAndGlobal resource also contains a record B60024E2 with `.ova`, `.ofc`
and `.ttt` strings alongside resource keys; their behavior is not decoded here.

## Record identity caveat

Duplicate keys occur in the inventories, including 057CC827 and 08001E29 in the
global resource. A dictionary that keeps only one record per key discards evidence.
The new comparison tool retains all record occurrences and all matching targets.
The camera parameter records discussed above have unique keys in their resource.
Duplicate handling must be considered before generalizing prior sample scripts.

## Evidence and reproduction

Local reports (excluded from Git): `menuboot-comparison`, `menucredits-comparison`,
`camera-global-comparison`, and `camera-comparison-audit/comparison.json`.
Each extraction/decoding manifest contains hashes and preserved tails. The audit
records SHA-256, lengths, record counts, duplicate keys and candidate GAO links.
New decoded SHA-256 values:

- MenuBoot: `a117670a09955632ba23fddc843a918d50090680c1e15a832c0b640560242914`
- MenuCredits: `800fffd139fa487d2dd1ebd056b3a5695abccf17d754a9559d1513f53cf82c63`
- CameraAndGlobal: `68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`

```powershell
python .\src\compare_camera_resources.py <new-report.json> <decoded-resource-1> <decoded-resource-2>
python .\tests\test_camera_resource_comparison.py
```

All five inventories consume their decoded inputs exactly using the envelope
validator. Two synthetic tests pass: duplicate retention and truncation rejection.
No general motion decoder or playback was added. Source game files remain read-only.

Next: follow Camera.gao's 057CC738 and 55000013 references, and compare their
relationship to the controller/behavior resources before assuming which camera
supplies the displayed transform. This is better supported than guessing a CF1
clock from a single sample.
