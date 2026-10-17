# DDS arrows and slider widgets — 2026-10-13

The menus now display the MGM-linked b_list_up/down arrows, footer/header
minus/plus buttons, surfacelink2 bar and Handle2 selector. The selector uses the
material REGION [40,16,88,112], then its declared 24x48 display dimensions before
the 1.25 page scale. Other sprites likewise use their material region and declared
dimensions. No replacement artwork is generated.

Sprite tint 0xFF7AA0BC is interpreted as ABGR (188,160,122,255), consistent with
the explicit text color and supplied captures. Slider assembly around a horizontal
centerline is a research interpretation; matching engine placement is not proven.

Observed ranges: ResolutionSlider 0..10, GammaSlider 0..100, MouseSlider 0..100.
Values are displayed as raw research units in the status bar. No resolution list,
gamma conversion or mouse sensitivity mapping is inferred. Selectors initially
sit at the minimum as a prototype convention, not a game default.

Click or drag the bar/selector; use minus/plus buttons, or Left/Right while the
slider has focus. Values clamp to the declared range. Graphics slider values are
shared between Effects and Advanced, and mouse slider values between Keyboard
and Gamepad. C clears the shared slider domain along with local research choices.
No settings are applied to the game or host display.

Up/down DDS arrows move focus among the six known action rows. They dim at the
first/last known row. This does not implement scrolling into additional actions:
their names and ordering have not been established. The original screenshot's
scrolling behavior remains future work.

Validation: widget bounds, clamping, shared values, pointer dragging beyond an
endpoint, minus stepping, keyboard adjustment, focus navigation and clearing all
pass in the GUI test. Previews were visually inspected. Existing five-page tests
remain applicable. Asset generation uses new reports, retaining earlier reports.
