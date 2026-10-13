# Interactive research viewer — 2026-10-13

The viewer displays an existing 800x600 prototype report in a fixed-size desktop
window. Python tkinter provides the window and input events; Pillow loads the
rendered prototype. PowerShell 5.1 provides the launcher. It reads report assets
without modifying game data and does not require a screenshot at launch time.

Controls:

- Up/Down and Tab/Shift+Tab move through six entries with wraparound.
- Mouse hover selects an entry; press and release on the same entry activates it.
- Enter/Space activate the current entry.
- Escape or the window close button exits the viewer.

Activation only reports a simulated action in the status bar. Even Quit is a
simulated game action; Escape closes the research viewer. No game process,
save access, scene loading or menu transition is implemented. Hit rectangles
are based on rendered ink plus five pixels, not verified original hit areas.
The focus outline is a diagnostic affordance, not a reproduced game effect.
Navigation order and wraparound are experimental. The original selection,
hover, pressed colors and animation remain to be implemented and verified.

From the repository root:

```powershell
.\tools\Show-MenuPrototype.ps1 -ReportDirectory '.\reports\your-menu-prototype-report' -PythonPath 'C:\Python\python.exe'
```

Requires Python with tkinter and Pillow. Generate the input report with
Export-MenuPrototype.ps1 first. The viewer does not embed an installation-specific
Python or report path. Add `-SmokeTest` to construct the widgets invisibly, test
navigation and mouse handlers, then close automatically.

Validation: three navigation-model tests pass. A Windows GUI smoke test passed
outside the restricted execution sandbox: image loading, widget construction,
wraparound, simulated activation, hit testing, hover selection, release outside
cancellation, click activation and window disposal. The sandboxed attempt could
not load Tcl initialization despite the files being present. This test does not
replace manual desktop interaction or establish original game behavior.
