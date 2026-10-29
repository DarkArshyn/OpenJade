# Apply native settings only after confirmation — 2026-10-29

The settings should take effect only after Back and Yes.
The Python model already separates its draft from saved settings, although the
optional legacy gamma bridge intentionally previews its draft. The native menu
had retained that immediate preview behavior by reading the draft each frame.

NativeMenu now exposes an AppliedDisplay snapshot derived exclusively from saved
settings. The Vulkan/window consumer uses it for gamma, filtering, window client
size and V-Sync. Widget values still reflect the draft while editing. Back/Escape
opens the existing confirmation only when the draft differs. Yes promotes and
persists the draft; No abandons it; Cancel keeps editing without affecting the
renderer. Default Settings also remains pending until confirmation. Unsupported
V-Sync requests are corrected in both saved and draft state when applied, rather
than repeatedly retried. The optional legacy Python bridge is unchanged.

The regression test exercises all four settings, confirmation opening, Cancel,
No, Yes, persisted-state reload and defaults. Thirty Rust tests pass. The native
GPU smoke also exercises a confirmed gamma/filter/resolution change. This change
implements the user's observed interaction contract; it does not claim a new
native executable trace of the original menu code.
