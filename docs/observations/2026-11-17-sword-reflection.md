# Sword reflection resources and sampled UV mapping

Date: 2026-11-17

Later follow-up: [Camera02 and Vulkan integration](2026-11-17-sword-vulkan.md).

## Verified observations

The GOG sword mesh `33001050` has triangle groups of 61, 8 and 24 triangles.
Material `13006BBB` references base texture `13006B64` at byte 44 and reflection
texture 2E011834 at byte 68. The latter resource decodes to a 32x32 first level;
its RGBA pixels exactly match the native stage-1 texture readback.

Stage 1 uses linear minification and magnification, clamp addressing in U/V,
and no mip filtering. Stage 0 uses wrapping and linear mip filtering.
These are captured sampler states, not assumptions based on texture dimensions.

Across eleven sampled visible draws (frames 0, 12, ..., 120), the two reflection
coordinate constant rows equal minus one half of the first two object-to-view
matrix rows' XYZ components, with a final component of 0.5. The maximum absolute
constant discrepancy is zero. Combined with the previously observed normal input
and shader outputs, the sampled UV relationship is:

    u = 0.5 - 0.5 * dot(object_to_view_row_x.xyz, object_normal)
    v = 0.5 - 0.5 * dot(object_to_view_row_y.xyz, object_normal)

Do not substitute the normalized lighting normal matrix: its captured entries
differ slightly. The following offscreen draw changes position constants while
retaining reflection constants; the visible-pass relationship must not be
asserted for every draw indiscriminately.

The [earlier shader arithmetic check](2026-11-13-ambient-cache-shaders.md)
established the two-texture composition. With a = base alpha and
K = (64, 71, 74)/255:

    RGB = 2 * ((1-a) * base.rgb * diffuse.rgb + a * reflection.rgb * K)
    alpha = (1-a)*a + a*reflection.alpha

## Reproduction and scope

Run with a private sword-reflectionb capture and a source manifest:

    python tests/integration_sword_reflection.py CAPTURE_DIRECTORY SOURCE_MANIFEST

The test checks resource references, readback equality, sampler states, record
extent and eleven visible-pass constant relationships. The capture record
SHA-256 is `54213e64a4f28aea5b88205e5dd6c3c650fa7b0321822d63f663c5d4be7b72b3`.
The original executable SHA-256 is
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Captures and original shader binaries remain private.

This observation does not implement reflection in Vulkan. Camera02 coverage,
the native construction of these constants, material slot remapping for the
other two groups, and final-pixel parity remain unverified. No runtime performance
claim follows from this resource/constant test.
