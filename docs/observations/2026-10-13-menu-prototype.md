# Static main-menu prototype — 2026-10-13

The logo decoded from POP.DDS and six labels generated from the MFT font are
assembled at 800x600 on a neutral background. Positions come from the MGM
files. The logo rectangle [15,15,399,111] is scaled by 1.25 and rounded to
[19,19,499,139]. No screenshot pixels are used in the reconstructed image.
This is an offline PNG prototype, not an interactive runtime or a complete
recreation of the original screen. The 3D background and version label are absent.

## Style experiment

Twelve variants combine nearest, bilinear, bicubic and Lanczos resampling with
no thickening, a one-pixel rightward max expansion before scaling, or the same
expansion after scaling. These are explicit experiments, not implementations of
the unknown BOLD behavior. They preserve the previously calculated positions;
no translation is fitted. This experiment thickens the assembled line mask,
not each glyph independently, and cannot establish the engine's font algorithm.

The same heuristic screenshot mask is evaluated at red thresholds 100/120/140.
At threshold 120 the mean Dice score across six labels is approximately:

| Variant | Mean mask overlap |
| --- | --- |
| Nearest, no expansion | 0.581 |
| Lanczos, no expansion | 0.572 |
| Bilinear, no expansion | 0.569 |
| Bilinear, source expansion | 0.546 |
| Bilinear, screen expansion | 0.537 |

The tested expansions do not provide a robust improvement. The small lead for
nearest does not prove the original filter: JPEG artifacts, mask thresholds,
subpixel rounding, unknown font selection and the capture's unknown build all
limit this metric. Scores are mask overlaps, not percentages of engine fidelity.
The main prototype retains the unmodified bilinear model. The highest-ranked
variant is exported separately as a diagnostic candidate.

## Reproduce

From the project root, using Windows PowerShell 5.1 and Python with Pillow and NumPy:

```powershell
.\tools\Export-MenuPrototype.ps1 -AssetRoot '.\reports\POPData-extracted\menu' -ReferenceImage 'C:\captures\menu.jpg' -OutputDirectory '.\reports\menu-prototype' -PythonPath 'C:\Python\python.exe'
```

Output must be new. The underlying comparison and DDS tools retain source hashes
and source copies in local reports. Outputs include prototype.png, its transparent
layer, a separate style-candidate.png, all twelve variant scores, logo geometry,
and the previous text-comparison diagnostics. Game data and the capture remain
read-only. No asset belongs in a public source repository.

Validation: three synthetic expansion tests cover coverage values, source
preservation, row boundaries and transparency. Artifact checks cover twelve
distinct variants with six labels, score bounds, image dimensions and background
transparency. The generated prototype was visually inspected.

Next: a small viewer using the established logo/text placement, followed by
selection-state experiments. Exact styling would benefit from lossless captures
and must remain provisional until verified.
