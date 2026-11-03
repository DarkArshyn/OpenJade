# Plante2 background contribution
Date 2026-11-03.

At framebuffer pixel (1010, 814), fixed menu camera and time zero, triangle
3560 of plante2 blends over triangle 798 of tronc1 (material 30000C95).
The leaf depth is 1.648 and the trunk depth is 7.411 camera units.
Marking triangle 798 changes the pixel; marking 800, 197, 4190, 4196,
12023 or 4205 does not. Disabling the fog panels also leaves it unchanged.

The normal RGB is (56, 87, 107). Black leaf RGB gives (5, 9, 13).
White leaf RGB gives (179, 183, 188), preserving texture and vertex alpha
in both experiments. Thus the effective source weight is about 0.684,
with a background weight about 0.316, subject to 8-bit rounding.
The reconstructed destination RGB is approximately (16, 28, 41).

Hiding the leaf instead yields (56, 83, 108). This is not the destination
at the original draw: removing its depth write permits subsequent draws.
Blackening later draws leaves the original pixel unchanged.
The contribution must therefore be measured in the existing draw order.

This measurement explains the Vulkan composite only. Correspondence to the
same covered triangle in the original video remains unverified.
No lighting or material values were changed by this investigation.

Correction: these measurements describe the earlier Vulkan depth-write behavior.
A [direct native capture](2026-11-03-native-mips-aligned.md) subsequently proved
that the GOG leaf does not write depth; fog3 contributes after it. The runtime
now follows that state. The old fog-exclusion result is not a native-game result.
