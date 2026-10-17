# Menu courtyard landmarks: diagnostic texture rendering

The balcony, foreground tree, distant tower and fake room can now be assembled
from the focused decoded Menu3D resource. This is an offline diagnostic, not the
original scene renderer or a verified camera reconstruction.

## Evidence

Input: `reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin`.
SHA-256: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
The script rejects other inputs. All offsets below are decimal, relative to the
mesh payload after its 12-byte record envelope.

| Landmark | GAO key | Mesh key | Vertex header offset | Vertices | Triangles |
| --- | --- | --- | ---: | ---: | ---: |
| Balcony | 30000CD9 | 30000C8C | 279420 | 14503 | 8898 |
| Tree | 30000CC1 | 30000C74 | 14112 | 407 | 507 |
| Distant tower | 30000CD8 | 30000C8B | 11492 | 367 | 306 |
| Fake room | 30000D41 | 30000D40 | 704 | 36 | 20 |

The final vertex records contain XYZ and UV as five float32 values. Every final
XYZ is a bit-exact member of the original position table. Indices are uint16
triples and consume the payload exactly. The group table immediately preceding
the final vertex header contains pairs of material slot and triangle count.
Their counts sum exactly to the final triangle count for all four objects.
Contiguous triangle assignment and zero-based material slots are interpretations
used by this diagnostic, not a general specification.

The balcony has 16 groups, including material slot zero. Selected objects have
identity candidate bases and zero auxiliary words; the preview adds their
candidate translations. The transform hierarchy remains unverified.

## Texture correction and limits

For format-word 5 candidates used here, BC1 blocks start at payload offset 60,
after the four bytes `00 00 00 C0` at offset 56. Treating offset 56 as the block
start produced visibly corrupted textures. The script checks that prefix.
Format-word 7 candidates use BC3 starting at offset 56. This is sample-specific;
the earlier ground BC1 experiment at offset 56 must not be treated as validation
of that offset or as proof that the actual texture is entirely transparent.

The synthesized slot-7 DDS was decoded independently using
`tools/Export-DDSPreview.ps1` under Windows PowerShell 5.1. Its RGBA pixels match
Pillow exactly (zero differing channels). This validates decoder agreement on
the selected bytes, not the original texture format as a whole.
Unsupported format-word 0 / slot 33 is shown in magenta.

## Comparison

Output: `reports/menu3d-landmarks-20261017/` (local, excluded from Git).
`Camera02-v0.png` shows the balcony and balustrade, the tree on the left and
a distant tower. `camera-comparison.png` contains Camera02, Balcony and Alternate,
each with unchanged and flipped V. `landmarks.obj` retains positions and UVs;
it does not assign materials. `landmarks.json` records keys, counts and choices.

The original French 800x600 main-menu screenshot supplied by the user is the
visual reference. The balcony is recognizable, but these views do not establish
the active camera. The 60-degree vertical FOV is chosen, not recovered. Basis-row
orientation, forward -Y and a shared translation space remain hypotheses.
Rendering uses perspective-correct UV interpolation, depth testing, near-plane
clipping, repeated nearest texture sampling and an alpha cutoff of 128.
There is no lighting, fog, animation or recovered material modulation.

## Reproduce and validate

```powershell
python .\src\preview_menu3d_landmarks.py <decoded.bin> <new-output-directory>
python .\tests\test_landmark_preview.py
```

Requires Python, NumPy and Pillow. Five synthetic tests cover multiple groups,
corrupt counts/indices/positions, truncation, clipped UV interpolation, and
depth ordering with transparent texels. The four real meshes pass the structural
checks during export. Inputs are read only; output must be a new directory.

Next: resolve camera/projection and transform-space evidence before tuning the
view by eye; identify slot 33's texture encoding and restore material behavior.
