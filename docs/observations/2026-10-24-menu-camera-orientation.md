# Menu camera orientation and readiness for a candidate 3D render

Date: 2026-10-24. Static analysis, not a captured runtime frame.

## Orientation path

Global camera behavior 00500C00 reads zone +0x100 through 0054A480. Both
balcony instances serialize 0, selecting the target-based branch. 00549DB0
reads the object reference at zone +0xD4 and adds the vector at +0xC8. The
caller adds zone +0x68 (zero in both instances; +0x1C8 is also zero), subtracts
the current camera position, and uses 00499E70 to normalize the direction.
Conditional thresholds and interpolation can preserve or smooth the previous
direction; the calculated target is not proof of the current frame direction.

The resulting direction is stored at global camera +0xA8/+0xAC/+0xB0.
00477540 receives that direction and up=(0,0,1), passes through 00693EC0 and
0079A040 to 00799790. For nondegenerate inputs, the basis it constructs is:

- Y = -normalize(direction)
- X = normalize(up cross direction)
- Z = X cross Y

The builder sets matrix flag bit 4. With its final argument zero, it does
not clear translation. The near-parallel case perturbs the up vector; this
fallback and the small-length normalization behavior are not reproduced by
the candidate script. The float sign changes appear as integer additions
of 0x80000000 in decompiler output; they are sign-bit changes, not angle conversions.

## Named targets and numerical candidates

| Zone | Target key/name | Target offset |
| --- | --- | --- |
| 30000D63 CAM_Balcony | 30000D65 Menu3D_FarahRoom_CAM_BalconyTarget.gao | (0,0,1) |
| 3C00144D CAMALT_Balcony | 3C00144E Menu3D_FarahRoom_CAMALT_BalconyTarget.gao | (0,0,0) |

Using stored GAO positions, ignoring hierarchy/runtime changes, and assuming
the settled direct branch gives:

| Candidate | Eye | Aim point |
| --- | --- | --- |
| CAM_Balcony | (-92.802040, -0.964916, 3.932158) | (-107.195572, -7.495495, 6.201583) |
| CAMALT_Balcony | (-97.717445, -6.916626, 3.183303) | (-107.454071, -4.805422, 4.027223) |

These are diagnostic candidate poses, not measured active menu poses. Neither
justifies replacing the preview defaults without an explicit comparison.

## Effective selection: not confirmed

The previous static chain establishes registration and selection mechanisms,
not which one runs in the stationary main menu. A bounded search of the
selected Menu3D token records found no literal object token (tag 01000028)
for either zone key. That does not exclude registration via current-object
context, event-driven selection, native code or other containers.

No live camera state was captured in this investigation. Zone +0x88, callback
scheduling, transition state, active zone +0x410 and active FOV remain unresolved.
To verify actual selection, observe the global camera object CC000403 in the
stationary menu, resolve its field-storage pointer via object +0x18 -> +4 ->
+0x44, and record +0x410, +0x1F0 and direction +0xA8. Map the selected runtime
pointer back to a named loaded GAO rather than comparing it to a resource key.
Also capture the attached object at camera entry +0x88, its matrix and the
entry FOV +0x94. Repeat after New Game to separate the balcony transition
from the stationary menu. This is a proposed validation procedure, not work
already executed.

## Readiness

A candidate offline 3D comparison is now justified using the existing extracted
geometry, the two explicit look-at poses and clearly labeled FOV hypotheses.
A faithful main-menu reconstruction is not yet validated. Remaining gates:

1. Observe or otherwise prove the stationary menu's active zone/pose and FOV.
2. Render candidates and compare multiple landmarks against the 800x600 capture.
3. Resolve material, lighting, transparency/fog and missing-object discrepancies.
4. Integrate the validated scene behind the existing menu simulation.

Audio, gameplay and the New Game transition are not prerequisites for the first
static visual comparison. They remain separate future work.

## Evidence

Local ignored evidence: reports/menu-orientation-20261024 contains four Ghidra
batches, inspect-menu-orientation.py and menu-orientation-candidates.json.
The script verifies the frozen Menu3D hash, resolves the target fields by
identifier, checks the branch values, and calculates orthogonal candidate
bases. It rejects degenerate vectors. These are static data and numerical
checks, not live-engine validation. Game files and preview defaults are unchanged.

See [vector and position transfer](2026-10-24-camera-vector-transfer.md) and
[zone registration](2026-10-24-camera-list-population.md) for the preceding chain.
