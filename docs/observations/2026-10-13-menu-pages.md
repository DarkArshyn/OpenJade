# Additional resource-based menu pages — 2026-10-13

The viewer now displays five linked MFT/DDS scenes: Options, Graphics / Effects,
Graphics / Advanced, Controls / Keyboard, and Controls / Gamepad. Sources are
the local PC GOG pop4common.mgm, extracted MFT/DDS resources, and the user-supplied
PopsotGraphics2.jpg, PoP_TSoT_Keyboard.png and PoP_TSoT_Controller.png captures.
The source code does not embed game assets or screenshot pixels.

## Evidence and interpretation

P_VideoMenu provides the layout slots for Effects and Advanced. The separate
P_VideoAdvanced contains a different set of effects and is not treated as the
page shown in the supplied Advanced screenshot. Filtering, V-Sync and Texture
Quality labels/options are transcribed from that screenshot into the observed
layout slots. catalog.json records every text substitution beside its original
stored string and records the screenshot filenames.

P_ControlsMenu contains six `New text` action labels and empty binding labels.
The six visible actions and their sample bindings are transcribed from the
keyboard/gamepad captures. These samples are not asserted to be game defaults.
The empty gamepad Walk Toggle slot is explicitly displayed as Unassigned.
Further action rows are unknown here; scrolling beyond the six samples is not
implemented. The existing Shadow Effects High/Low/None discrepancy is retained.

Positions, caption definitions, text height, fonts and texture panels come from
the MGM. Fixed-width centered text aligns within its LEFT/RIGHT bounds;
autosized captions retain their instance anchor. This distinction prevents
action labels from overlapping the left tabs. The controls binding fields use
Atlantis MF Regular 28; titles and other captions use the declared fonts.
All rendering remains at 800x600. Baseline, filtering and panel modulation are
research interpretations, not verified game rendering. Supported panel flips
and 180-degree rotations are applied, but this is not a general MGM renderer.

## Interaction and limits

Options opens Graphics or Controls. Effects and Advanced tabs switch pages;
Keyboard and Game Pad switch control pages. Tab/arrows move the diagnostic focus,
Enter/Space activate, mouse press/release on the same item activates, and Escape
or Back returns to Options then to the main viewer. These transitions are
explicit prototype behavior rather than recovered game action code.

Advanced exposes seven choices across three independent groups. Graphics and
camera choices start unset. Clicking a binding opens a standard research text
dialog accepting 1-24 printable ASCII characters. No hardware capture, key
remapping, controller detection or game-file write occurs. Changes survive page
switching but disappear when the Options window closes. C clears changes for the
current page and restores screenshot binding samples, not game defaults.

Resolution, gamma and mouse-speed labels are visible, but their controls are not
implemented. The original 3D background, scrolling action list and Default
Settings command are absent. Sounds and Game remain greyed out. The font size
and screen proportions are not fitted to the supplied 1920x1080 captures.

## Build and launch

Generate into a new menus-assets directory inside an existing prototype report:

```powershell
.\tools\Export-MenuPages.ps1 -AssetRoot '.\reports\POPData-extracted\menu' -OutputDirectory '.\reports\your-prototype\menus-assets' -PythonPath $PythonPath
.\tools\Show-MenuPrototype.ps1 -ReportDirectory '.\reports\your-prototype' -PythonPath $PythonPath
```

Windows PowerShell 5.1 and Python with Pillow are needed for generation; tkinter
is needed for the viewer. Existing decoders export validated atlas pixels, glyph
tables and DDS images. Source SHA-256 hashes are recorded and checked after the
build. The viewer requires the catalog MGM hash to match its prototype report.
Reports without menus-assets retain the earlier viewer behavior.

## Validation

Five model tests pass: no assumed defaults, exclusive/page-isolated choices,
binding validation, invalid-choice rejection and page-local clearing. Integration
checks verify five scene dimensions and in-bounds hit areas, eighteen editable
binding fields, and seven Advanced choices. Alpha pixels for all six original
menu labels match the PowerShell specimen renderer exactly at native scale.
Advanced and both Controls previews were visually inspected; this caught and
corrected the fixed-width center alignment. The Windows GUI smoke test passes
five-page navigation, graphics choices, separate keyboard/gamepad edits, return
and disposal. Original game behavior remains unverified.
