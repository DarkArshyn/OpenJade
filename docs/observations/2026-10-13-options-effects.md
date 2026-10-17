# Options / Effects research panel — 2026-10-13

Activating Options in the main viewer opens a research window. Graphics / Effects
opens four choice groups read from P_VideoMenu in pop4common.mgm. Back/Escape
returns to Options, then to the main menu. This navigation is implemented by the
viewer and is not inferred from MGM action code. Widgets use a system font and
native controls; this is a behavioral experiment, not a visual reconstruction.

Observed groups: SpecialEffects (High/Medium/Low), Shadow Effects (High/Low/None),
Water Effects (On/Off), Fog (On/Off). Empty third choices for water and fog are
omitted. The supplied Effects screenshot instead shows High/Medium/None for
shadows. The difference is retained, not silently corrected. Its cause is unknown.
P_VideoAdvanced contains a different collection of individual effects and must
not be assumed to match the supplied Advanced screenshot solely from its name.

All choices initially remain unset. MGM DEFAULT fields and screenshot selections
are not treated as game settings defaults. Selection is exclusive per group;
values remain in memory while the Options window is open, including when moving
back and forth. Closing it discards the values. Clear research choices clears the
model; it does not claim to implement the game's Default Settings command.
Resolution, gamma, Advanced, input bindings and audio are not implemented here.
No Hardware.ini or game file is written. Source MGM hash is checked against the
prototype report before reading.

Validation: four model tests cover unset values, exclusive selection, clearing
and invalid choices. Real-data checks cover four groups and ten choices. The GUI
smoke test covers opening Options, opening Effects, retaining choices across
navigation, clearing and returning to the main viewer.
