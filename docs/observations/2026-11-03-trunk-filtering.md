# Tronc1 texture filtering
Date 2026-11-03.

The GOG indexed draw was identified using hash 18F4D6A2, 128 triangles
and the tronc1 model-view depth translation 7.43505. Live states show a
256x256 DXT1 texture with six mip levels, wrap addressing, linear minification,
magnification and mip filtering, zero LOD bias, no alpha test, no alpha blending
and enabled depth writes.

Resource 30000C5C stores the BC1 base level at payload offset 60.
Decoding its 65,536 RGBA texels reproduces material-3.png exactly.
Six contiguous native levels were decoded down to 8x8.
This resource's offset differs from the leaf BC3 data offset of 56.

At framebuffer (1010,814), triangle 798 has UV (0.48683549,0.88996386).
A CPU derivative estimate gives 1.097 and 1.142 texels per pixel, or LOD 0.19177.
Bilinear RGB at the base level is (147.663,148.865,147.663); interpolating the
first two native levels gives (149.780,150.985,149.780).
This approximately 1.43 percent change is an estimate before diffuse
modulation and leaf compositing. It does not explain the full remaining
image discrepancy. The estimate has not been compared to GPU-selected LOD.

The current default Vulkan draw still uses the base level for this trunk.
Native mip integration and a screen-aligned GOG/Vulkan comparison remain pending.
No renderer settings were changed in this investigation.

Follow-up: [native integration and aligned capture](2026-11-03-native-mips-aligned.md)
now complete the pending integration and correct the leaf depth-write assumption.
The base-level-only statement above describes the earlier audit state.
