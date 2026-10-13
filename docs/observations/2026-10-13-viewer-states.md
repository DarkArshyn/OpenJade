# Viewer state colors — 2026-10-13

The viewer now reads each button's LINK/AREA, TIMINGS and corresponding caption
KEYFRAME/COLOR from the two MGM files recorded in experiment.json. SHA-256 is
checked before use; changed source files require a new prototype report.
The original resource paths must remain available. No game data is modified.

All six tested definitions declare these RGBA colors:

| State | Frame index | RGBA |
| --- | --- | --- |
| ENABLED | 0 | 188 160 122 255 |
| PRESSED | 10 | 255 255 255 255 |
| DISABLED | 20 | 102 102 102 255 |
| SELECTED | 30 | 188 160 122 255 |
| OVER | 40 | 232 220 193 255 |

These are verified file values, not proof of original event timing. The viewer
uses experimental precedence: disabled, pressed, hovered, selected, enabled.
Text alpha and positions remain from the existing bilinear specimen. A selected
entry retains the diagnostic outline because SELECTED and ENABLED colors match.
Mouse press/release and keyboard press/release display pressed color. A research
checkbox previews disabled colors and blocks all simulated activation. Focus
loss clears pending input. Activation still reports a simulated action only.
Options transitions and original-game input behavior are not implemented.

Validation: three state-model tests cover normal states, precedence and dragging
away. All six real palettes were checked. The Windows GUI smoke test exercises
mouse cancellation/activation, keyboard press/release and disabled activation
blocking. Three existing navigation tests remain unchanged.

Launch with Show-MenuPrototype.ps1 as before. The Python/tkinter viewer remains
a research tool, not a commitment to the future game runtime's language.
