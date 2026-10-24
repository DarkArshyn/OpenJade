# Balcony vectors and transfer to the global camera

Date: 2026-10-24. Read-only static analysis of the frozen inputs.

## Vector meanings

Let B be the 3x3 linear transform whose columns are the stored basis triplets
at matrix offsets 0x00, 0x10 and 0x20; p is the position returned by 00475FB0.
For the direct, non-hierarchical case:

- Zone +0x1DC..+0x1E4 is minus the second basis triplet. 00693F40 flips each
  float sign bit at matrix +0x10/+0x14/+0x18. These are not Euler angles.
- Zone +0x210..+0x218 is B-transpose times p when the linear-transform flags
  are active. 0049A300 -> 0079A900 -> 0079A880 transposes the 3x3 basis using
  0079AD50, then 0079A230 multiplies the vector by that transposed basis.
  The translation computed by 0079A880 is NOT used by 0079A230. Thus this is
  not the usual affine local point B-inverse*(p-translation), and is not
  necessarily zero for an object referring to itself.

0079A230 copies its input unchanged if matrix flags & 0x3C are zero. Otherwise
it computes x'=m[0]x+m[4]y+m[8]z, y'=m[1]x+m[5]y+m[9]z,
z'=m[2]x+m[6]y+m[10]z. Its in-place path preserves the original components.
The transpose equals an inverse only for an orthonormal basis. Hierarchical
branches in 00475FB0 and 004778F0 compose ancestor transforms; do not silently
replace them with the direct formulas.

## Proven position path

The global camera behavior B6002512 -> 00500C00 reads its selected zone from
+0x410 and calls:

1. 005602E0(zone, result, proposed position). For zone mode 2 it reads the
   current position of zone reference +0x18C using 00475FB0.
2. 0054A0F0 converts the proposed and reference positions with 0049A300,
   chooses components according to zone +0x20, then converts back through
   0049A3E0 -> 0079A230 using the original matrix.
3. 00548B10 optionally clamps the result when zone +0x114 is nonzero.
4. 00500C00 can pass the result through 005C0D60 on its transition branch,
   or use it directly. It stores the resulting position at global camera
   +0x180/+0x184/+0x188.
5. If zone +0x1C0 is zero and global camera +0x1F0 is not 1, it calls
   00476260(current camera object, result). That calls 006940A0, which writes
   the object's matrix translation at +0x30/+0x34/+0x38 and sets flag bit 2.
   Other branches call 005ADC30 and are not equated with this direct path.

The two balcony instances inherit definition defaults +0x20=0, +0x114=0,
+0x1C0=0. Mode 0 in 0054A0F0 selects all three reference components. Therefore
its result is B*(B-transpose*p), equal to p for an orthonormal basis; the
clamping helper leaves it unchanged with +0x114=0. These are serialized
initial values, not observed runtime values.

This path relieves a previous ambiguity: the position is recomputed from the
referenced object's current transform. No direct transfer of the cached
zone +0x210 or +0x1DC vectors was established in this path. In particular,
the initialized negative-axis vector is not yet proven to become the camera's
view direction. The later orientation update is a separate investigation.

## Evidence and limits

Local evidence: reports/camera-vector-transfer-20261024 contains six Ghidra
batches and mathematical checks. Inputs retain the hashes recorded in
[the pose-reference report](2026-10-24-balcony-zone-pose.md). The selected
zone branch is conditional: actual main-menu selection, +0x88 eligibility,
runtime modifications, scale and the final orientation remain unverified.
No preview or game data was modified.

Next: follow orientation inputs into the 00477540 call later in 00500C00,
then connect the resulting object matrix to the previously verified render
camera attachment. Do not declare the rendered main-menu pose reproduced yet.
