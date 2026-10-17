# Screenshot-driven menu simulation — 2026-10-16

## Reference

17 original-game PC GOG French screenshots at 800x600
on 2026-10-16: Profil Creation, Main Menu, Options, four Keyboard Options views,
four Game Options views, Save Modifications, Advanced Graphics,
Effects Graphics, Sound, Change Profile and Quit Game.
Earlier user-supplied Gamepad captures supplement the keyboard references.
These images are not copied into the repository or distributed.

## Implemented simulation

`Show-MenuSimulation.ps1` now opens profile creation. Create a session profile to
reach the main menu. The simulation includes Options, Effects, Advanced, Keyboard,
Gamepad, Game, Sound, profile creation and profile selection in the same window.
The controls list contains all eighteen actions visible across the four captures.
Arrows advance five rows with overlap; the wheel advances one row. These step
sizes are simulation decisions, not measured original-game behavior.

Text uses the extracted MFT font. DDS resources supply the logo, panel silhouette,
sliders, arrows, EAX logo and a cursor candidate. Text is fitted to the
800x600 screenshot layout. Confirmation pages use MFT text and DDS panels rather
than native dialogs. Keyboard editing and profile entry are drawn in the canvas.

Settings support edits, a Default Settings button, and save/discard/cancel when
leaving modified settings. Defaults reset the simulation's baseline for the
relevant settings family. Shared graphics and controls values stay synchronized.
Cancel stays on the edited page; that behavior remains an explicit assumption.
Quit requires confirmation. Profile creation, selection and confirmed deletion
operate only on a session list (maximum five); no original profiles are read.
Settings are shared by simulation profiles, not stored per profile.

## Fidelity limits

- The 3D scene is absent; a neutral background remains. No screenshot is used as
  a substitute game renderer. Layout coordinates are transcribed, not recovered
  runtime placement rules. This is not pixel-identical reproduction.
- `officialcursor_alpha2_desaturated.dds` is a provisional cursor selection;
  its identity, hotspot and animation have not been conclusively established.
- Values visible in captures initialize the simulation. They are not proof of
  factory defaults. Resolution choices and gamma increments are simulated.
- The keyboard labels preserve the observed French AZERTY keys. Gamepad actions
  beyond the earlier six-row capture have empty bindings rather than guessed keys.
  Editing changes labels only; no hardware assignment is performed.
- EAX is displayed disabled, as in the supplied capture. No audio/graphics setting
  affects hardware or the original game.
- Profiles and settings are lost on exit. There is no installation Profiles scan.
- Load is disabled because no simulated save exists. New Game and Credits lead
  to an explicit runtime-unavailable placeholder; no reference screen for either
  was supplied. Background animation and transition timing remain unimplemented.

## Verification and launch

Four model tests check profile validation, complete action traversal, transactional
restoration and isolated defaults. Rendering checks exercise ten screens, validate
click bounds and ensure confirmation hit targets exclude underlying controls.
The GUI smoke test covers all screens, profiles, the last action binding, scroll
bounds, save/discard/cancel and quit Yes/No, and verifies no child Toplevel exists.
Rendered previews were visually inspected for label collisions and panel bounds.

```powershell
.\tools\Show-MenuSimulation.ps1 -ReportDirectory <prototype-report-with-menus-assets> -PythonPath <python-with-Pillow>
```

Add `-SmokeTest` to run the automated GUI check. Run
`python tests/test_simulation_screens.py <report-directory>` for model/render tests.
All original game resources remain read-only. No external images or assets are
added to source control.
