# Effects resource-based canvas — 2026-10-13

Effects now uses the original MFT glyphs and DDS panels instead of native radio
buttons when an effects-assets directory is present in the prototype report.
The Options hub remains a research widget screen. The canvas is fixed at 800x600
with the existing 640x480-to-800x600 coordinate transform and text baseline
hypothesis. Text labels, caption links, sizes, alignment and positions come from
P_VideoMenu and referenced definitions. Packed ARGB panel modulation is an
experimental interpretation. No 3D background is recreated.

Ten non-empty choices and Back are clickable; Tab/arrows move a diagnostic focus
rectangle and Enter/Space activate. Esc returns and C clears research choices.
Selection stays in memory. Chosen entries are white and hovered entries pale
beige; this is provisional interaction styling, not complete checkbox animation.
No game configuration is written. The MGM/capture Shadow Effects discrepancy is
preserved. Native controls remain the fallback for reports without these assets.

The upper panel is intentionally empty: resolution and gamma controls are not
implemented. Default Settings and Advanced are also absent. Font sizes from the
MGM produce smaller text than the supplied screenshots; no per-label size fitting
has been applied. This remains a partial Effects reconstruction.

Generate assets into a new directory with Python, Pillow and Windows PowerShell
5.1 available (the builder invokes the existing validated MFT/DDS exporters):

```powershell
& $PythonPath .\src\build_effects_assets.py .\reports\POPData-extracted\menu .\reports\your-prototype\effects-assets
.\tools\Show-MenuPrototype.ps1 -ReportDirectory .\reports\your-prototype -PythonPath $PythonPath
```

The generator clears inherited PSModulePath only in child-process environments
so Windows PowerShell discovers its own standard modules. It preserves source
copies and hashes through existing exporters. layout.json records the MGM hash;
the viewer rejects a layout from a different report revision.

Validation: generated preview visually inspected; GUI smoke test passed. The
styled-control test verifies eleven interactive controls, exclusive model choice,
return, persistence across navigation and clearing.
