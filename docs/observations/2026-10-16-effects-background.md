# Effects background correction — 2026-10-16

The user's viewer screenshots confirmed the remaining dark overlap in Effects.
The previous fix excluded the tall panel only in Advanced and left both panel
instances active in Effects. Effects now retains only ShmueButton (545x200),
covering all four rows including Fog, and excludes ShmueButton2 (545x155).
Advanced continues to use only the shorter panel. The choice follows the supplied
captures; the runtime visibility rule has not been recovered from game code.

Validation: regenerated Effects preview inspected; the Fog row remains inside
the tall panel and the dark overlap is gone. Advanced, Options, Keyboard and
Gamepad backgrounds remain byte-identical to the previous corrected report.
The upper Effects panel remains unchanged. Existing scene/model checks pass.
Original MGM/DDS resources and earlier reports remain unchanged.
