# Menu_Start_Demo copies Camera02 into the global camera

Date: 2026-10-24. Hash-checked static analysis; no live callback trace.

## Verified resource and native chain

Menu_Start_Demo.gao (0B0044CA) references wrapper 0B0044DF, whose pair is
0B0044DD / 0B0044DE. The behavior list links OFC 0B0044DC, bound in POP.EXE
to 0059F140. Instance field identifier FFE2CDA7 maps to definition offset
+0x258 and contains Camera02 key 30000CF0 (object tag 28).

0059F140 resolves global camera CC000403 into DAT_00ADBD18. Its object-field
array access [0x96] is offset 0x258. Near the end of the behavior it:

1. Reads the referenced object's position with 00475FB0.
2. Reads its negative second matrix axis with 004778F0.
3. Reads its normalized third matrix axis with 00477DA0 -> 00693FC0.
4. Applies the position to CC000403 with 00476260.
5. Applies direction and up to CC000403 with 00477540.
6. Calls 00483CD0(0, 0x3FA66666), setting angle float32 1.2999999523 radians.

This establishes a concrete menu-behavior path from Camera02 to the global
camera, independently of the balcony candidate list. It does not prove callback
scheduling, the final animation/hierarchy state of Camera02, or persistence of
these values at the captured frame. The previous statement that no such static
pose-source link was known is superseded by this result.

## Related insertion chain

Menu_Start_Demo instance +0x6CC points to 30000D68,
Menu3D_FarahRoom_CAMCUTMAN_Balcony@CAM_Insert.gao. Its wrapper 30000D67 links
behavior list 030040BF and instance 30000D66. Field +0x48 in that instance
also references Camera02. In 0061A600, a branch with event discriminator 0x32
and value 999 posts event 0x6E to the +0x6CC object. The branch's user-facing
meaning is not established here and must not be named New Game without proof.
This supports investigating the insertion/animation path separately from the
menu pose-copy behavior.

## New render comparison

Two unadjusted stored-Camera02 renders reuse 42 objects, 14,960 triangles and
35 materials, with yaw and pitch adjustments both zero. The traced angle is
rendered under two explicit projection hypotheses:

- vertical angle: vertical FOV 74.4845 degrees;
- horizontal angle at 4:3: vertical FOV approximately 59.38 degrees.

Neither is asserted to be the runtime projection branch. The existing native
projection study records a branch and ratio that still need mapping to the
current diagnostic rasterizer. Stored transforms also need not equal runtime
transforms after motion-track processing.

Both renders recover a wider courtyard view than the balcony candidates.
They still differ from the original screenshot in landmark placement,
left/right arrangement, lighting and fog. The discrepancy suggests checking
axis conventions before adjusting camera yaw or moving scene objects; it is
not proof that the source scene is mirrored. No image mirroring was applied.

## Validation and artifacts

Local ignored directory: reports/camera02-menu-startup-20261024.
It contains four Ghidra batches, a validator and JSON result, and two rendered
views with comparison.png. The validator checks executable and Menu3D hashes,
the typed GAO-to-behavior chain, native binding and Camera02 instance reference.
The two renders completed and their comparison sheet was visually inspected.
Game resources and existing preview defaults are unchanged.

Next: reconcile the diagnostic view axes with the native -B0/-B2/-B1 conversion
and projection signs, then establish the projection branch and Camera02 motion
state. Runtime selection is still not directly captured, but the pose-copy
source is now supported by code and typed resource links.
