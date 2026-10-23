# External reference: kugelrund/io_scene_pop

Reviewed 2026-10-20. Author: kugelrund and contributors.
Pinned master revision: `d6b685e2751c3c42acdda8f25677e3beabb4381b`.

[README](https://github.com/kugelrund/io_scene_pop/blob/d6b685e2751c3c42acdda8f25677e3beabb4381b/README.md)
describes a Blender importer for decompressed WOL/WOW resources from the Sands
trilogy. The repository supplies an MPL-2.0 LICENSE. This comparison imports no
external source files and does not require Blender.

The GAO branch in [popmap.py](https://github.com/kugelrund/io_scene_pop/blob/d6b685e2751c3c42acdda8f25677e3beabb4381b/popmap.py#L318-L377)
uses flag 0x4000 to read direct geometry/material-pack keys, after the transform
and bounding-volume data. Flag 0x80000 adds another pair of triplets before the
keys. These are external format hypotheses, checked against our frozen resource.
The importer also assigns materials by mesh group. Its rendering choices are not
proof of the original game's rendering behavior.

## Menu3D verification

The independent reader `src/inspect_menu_scene_links.py` retains our existing
length-bounded record scanner and validates the input SHA-256. It preserves
duplicate-key counts rather than choosing an arbitrary record.

Of 109 GAO records, 72 enter the direct-link branch and 37 are excluded. Of the
72, 55 resolve unique geometry and material-pack records with geometry header
(1,7) or (1,8). This is header/link validation, not full mesh decoding. All 72
geometry keys resolve uniquely; 71 material-pack keys resolve uniquely. Camera02
has no matching material-pack record. The 17 unsupported geometry headers are
retained in the report, not rendered or silently discarded.

The five previously investigated landmarks agree exactly:

| Object | Geometry key | Material pack | Link payload offset |
| --- | --- | --- | ---: |
| 30000CD9 balcony | 30000C8C | 30000CB3 | 175 |
| 30000CC1 tree | 30000C74 | 30000CB3 | 164 |
| 30000CD8 distant tower | 30000C8B | 30000CB3 | 179 |
| 30000D41 fake room | 30000D40 | 30000CB3 | 166 |
| 30000CC7 fog panel | 30000C7A | 30000CB3 | 166 |

Keys are hexadecimal. The link offset is N+122, plus 24 with flag 0x80000,
where N is the stored name length. Only compact version-10 GAOs in the frozen
resource are covered. These records are candidates for scene assembly, not
proof of visibility, world-space placement or active membership.

```powershell
python .\src\inspect_menu_scene_links.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\menu-scene-links-new.json
python .\tests\test_menu_scene_links.py
```

Two synthetic tests cover both bounding-volume extents, truncated records and
objects without direct links. Real-data output: `reports/menu-scene-links-20261020.json`.
Next: validate geometry and material groups for these 55 candidates, then assemble
them under a documented fixed camera. Camera gate 276 is not a prerequisite.
