# Main-menu text comparison — 2026-10-13

Sources: 800x600 original menu capture, local PC GOG
pop4mainmenu.mgm, pop4common.mgm and Atlantis MF Regular 36 MFT. It is not included in source code.
Generated reports record absolute input paths and SHA-256 hashes locally.

## Reconstruction

`tools/Compare-MFTMenu.ps1` resolves six named button instances to their common
caption definitions, using frame 0. It invokes the existing MFT specimen tool.
The Python helper requires Pillow and NumPy (tested with 12.3.0 and 2.3.5).
This bounded experiment accepts XML-compatible MGM and an 800x600 capture;
it is not a general MGM renderer.

Page scaling is 800/640 = 600/480 = 1.25. Caption HEIGHT is 18 and font size
word is 36, giving the experimental glyph scale 18/36*1.25 = 0.625.
The baseline hypothesis is `(buttonY + captionTOP + HEIGHT) * 1.25`.
The renderer crops the existing specimen's ink, applies bilinear resampling,
and uses frame-0 color. It does not implement BOLD=1, shadows or game filtering.
The displayed reconstruction has no empirically fitted translation applied.

| Label | Predicted rounded ink origin | Best diagnostic translation |
| --- | --- | --- |
| Start New Game | 376, 162 | 0, 0 |
| Load Saved Game | 377, 224 | 0, 0 |
| Options | 377, 286 | 0, 0 |
| Credits | 377, 350 | 0, 0 |
| Quit | 378, 411 | 0, 1 |
| Change Profile | 63, 536 | 1, 0 |

Translations are selected in a bounded -4..4 pixel search against a heuristic
text mask, not exact measurements of the original glyph origins. The observed
agreement supports the placement and scale hypotheses for this capture.
It does not prove exact baseline semantics, kerning, font selection or filtering.

## Contours and limitations

The reference mask uses R-B>5, R>=G, R>120. The specimen uses alpha>=64.
Dice overlap is computed in a fixed padded rectangle: twice the intersection
divided by the total mask areas. Unadjusted scores range from approximately
0.45 to 0.73; these are diagnostic mask overlaps, not game accuracy percentages.
Red-channel thresholds 100, 120 and 140 are also reported to expose sensitivity.
Four labels keep a best translation of (0,0) across all three thresholds;
Change Profile keeps (1,0), while Quit changes from (0,0) to (0,1).
The initial stricter color mask missed much of the desaturated JPEG text and
was discarded. JPEG artifacts and background colors prevent ground-truth
pixel validation. No hand adjustment of individual glyphs was applied.

`comparison.png` shows reference crops, unadjusted specimens, and contour
overlays (red = reference mask, cyan = fitted specimen, white = overlap).
`menu-text.png` is a transparent text-only 800x600 reconstruction;
`menu-preview.png` adds a neutral background. `comparison.json` records
positions, overlap scores and threshold sensitivity. The screenshot itself
is not used as the reconstructed menu background.

## Reproduction

```powershell
.\tools\Compare-MFTMenu.ps1 -AssetRoot '.\reports\POPData-extracted\menu' -ReferenceImage 'C:\captures\menu.jpg' -OutputDirectory '.\reports\menu-comparison' -PythonPath 'C:\Python\python.exe'
```

Output must be new and outside game/. Input hashes are checked after the run.
Four independent metric tests cover identical, disjoint, partial and empty
masks. Six real labels were generated and visually inspected. Existing MFT
and specimen regression tests remain applicable.

Next: investigate bold styling and subpixel sampling with a lossless capture,
then assemble the logo and text on a neutral background. The original 3D scene,
menu states, animation and input behavior remain separate, unimplemented work.
