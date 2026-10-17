# Advanced background correction — 2026-10-16

The supplied PopsotGraphics2.jpg shows one lower panel around three option rows.
The generator previously composited both P_VideoMenu panel instances: ShmueButton
(545x200) and ShmueButton2 (545x155, rotated 180 degrees). Their overlap produced
an extra dark inset and the longer panel extended below the Advanced controls.

Advanced now excludes ShmueButton and retains the shorter ShmueButton2 instance.
The upper resolution/gamma panel remains. Effects and all other pages are
unchanged. The exclusion is recorded in catalog.json as excluded_background_nodes.
This visibility decision follows the screenshot; the MGM itself does not establish
the runtime switching rule. The original MGM and DDS files are not modified.

Validation: regenerated Advanced preview visually compared with the reference;
the other four backgrounds remain byte-identical to the previous generated PNGs.
The upper Advanced panel remains pixel-identical; its lower panel no longer has
the extra overlap or extension. Existing menu scene/model checks pass.
