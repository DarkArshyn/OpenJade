//! Ordered local-space fixture deformation, using stored mesh alpha weights.
use crate::{
    invalid,
    palms::{self, PalmVertex},
};
use std::io;

pub(crate) struct Fixture {
    local: [f32; 3],
    weight: f32,
    basis: [[f32; 3]; 3],
    modifiers: [[f32; 4]; 2], // amplitude, spatial factor, rate, phase
}

// The native x87 expression rounds once when the new phase is stored.
fn advance_phase(phase: f32, rate: f32, dt: f32) -> f32 {
    let mut next = (f64::from(phase) + f64::from(rate) * 30. * f64::from(dt)) as f32;
    let tau = std::f32::consts::TAU;
    if next > tau {
        next -= tau;
    } else if next < 0. {
        next += tau;
    }
    // Fixed-time research captures may advance farther than one native frame.
    if !(0. ..=tau).contains(&next) {
        next = next.rem_euclid(tau);
    }
    next
}

impl Fixture {
    pub(crate) fn advance(&mut self, dt: f32) {
        for m in &mut self.modifiers {
            m[3] = advance_phase(m[3], m[2], dt);
        }
    }
    fn local_position(&self) -> [f32; 3] {
        let mut p = self.local;
        let [amplitude, spatial, _, phase] = self.modifiers[0];
        let a = spatial * p[0] + phase;
        let amplitude = amplitude * self.weight;
        p[1] += amplitude * palms::wave(a, 0);
        p[2] += amplitude * palms::wave(a, 256);
        let [amplitude, spatial, _, phase] = self.modifiers[1];
        let a = spatial * p[2] + phase;
        p[0] += amplitude * palms::wave(a, 0);
        p[1] += amplitude * palms::wave(a, 256);
        p
    }
    pub(crate) fn position(&self, base: [f32; 3]) -> [f32; 3] {
        let p = self.local_position();
        std::array::from_fn(|axis| {
            base[axis]
                + (0..3)
                    .map(|i| (p[i] - self.local[i]) * self.basis[i][axis])
                    .sum::<f32>()
        })
    }
}

pub(crate) fn decode(
    bytes: &[u8],
    vertices: &[f32],
    existing: &[PalmVertex],
) -> io::Result<Vec<PalmVertex>> {
    if bytes.len() < 44 || &bytes[..8] != b"OJFIX001" {
        return Err(invalid("Invalid fixture header"));
    }
    let count = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    if count == 0 || count > 4096 || bytes.len() != 44 + count * 56 {
        return Err(invalid("Invalid fixture extent"));
    }
    let f = |b: &[u8]| f32::from_le_bytes(b.try_into().unwrap());
    let params: [f32; 8] = std::array::from_fn(|i| f(&bytes[12 + i * 4..16 + i * 4]));
    if params.iter().any(|v| !v.is_finite() || v.abs() > 1000.) {
        return Err(invalid("Invalid fixture parameters"));
    }
    let modifiers = [
        params[..4].try_into().unwrap(),
        params[4..].try_into().unwrap(),
    ];
    let mut used: std::collections::HashSet<usize> = existing.iter().map(|v| v.index).collect();
    let mut result = Vec::with_capacity(count);
    for record in bytes[44..].as_chunks::<56>().0 {
        let index = u32::from_le_bytes(record[..4].try_into().unwrap()) as usize;
        let values: [f32; 13] = std::array::from_fn(|i| f(&record[4 + i * 4..8 + i * 4]));
        if index >= vertices.len() / 9
            || !used.insert(index)
            || values.iter().any(|v| !v.is_finite() || v.abs() > 10000.)
            || !(0. ..=255. / 256.).contains(&values[3])
        {
            return Err(invalid("Invalid fixture vertex"));
        }
        let fixture = Fixture {
            local: values[..3].try_into().unwrap(),
            weight: values[3],
            basis: std::array::from_fn(|i| values[4 + i * 3..7 + i * 3].try_into().unwrap()),
            modifiers,
        };
        result.push(PalmVertex::fixture(
            index,
            vertices[index * 9..index * 9 + 3].try_into().unwrap(),
            fixture,
        ));
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn second_wave_reads_deformed_z_and_scaled_basis() {
        let f = Fixture {
            local: [0.; 3],
            weight: 0.5,
            basis: [[2., 0., 0.], [0., 3., 0.], [0., 0., 4.]],
            modifiers: [[2., 0., 0., 0.], [1., std::f32::consts::FRAC_PI_2, 0., 0.]],
        };
        let p = f.position([10., 20., 30.]);
        assert!((p[0] - 12.).abs() < 1e-5);
        assert!((p[1] - 20.).abs() < 1e-5);
        assert!((p[2] - 34.).abs() < 1e-5);
    }
    #[test]
    fn rejects_truncated_and_duplicate_vertices() {
        let mut b = b"OJFIX001".to_vec();
        b.extend(2u32.to_le_bytes());
        b.extend([0u8; 32 + 112]);
        assert!(decode(&b, &[0.; 9], &[]).is_err());
        b[8..12].copy_from_slice(&1u32.to_le_bytes());
        b.truncate(100);
        let decoded = decode(&b, &[0.; 9], &[]).unwrap();
        assert!(decode(&b, &[0.; 9], &decoded).is_err());
        assert!(decode(&b[..99], &[0.; 9], &[]).is_err());
        b[28..32].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(decode(&b, &[0.; 9], &[]).is_err());
    }
    #[test]
    #[ignore = "Requires the local hangfire capture and prepared scene"]
    fn native_fixture_chain() {
        let scene = std::path::PathBuf::from(std::env::var("OPENJADE_FIXTURE_SCENE").unwrap());
        let capture = std::fs::read(std::env::var("OPENJADE_FIXTURE_CAPTURE").unwrap()).unwrap();
        let mesh = std::fs::read(scene.with_file_name("fixture-native-mesh.bin")).unwrap();
        let mut scene = crate::Scene::load(&scene).unwrap();
        let f = |b: &[u8], at: usize| f32::from_le_bytes(b[at..at + 4].try_into().unwrap());
        assert_eq!(capture.len() % 800, 0);
        let mut maximum = 0f32;
        let mut checks = 0;
        for pair in capture.as_chunks::<1600>().0 {
            assert_eq!(u32::from_le_bytes(pair[4..8].try_into().unwrap()), 21);
            assert_eq!(u32::from_le_bytes(pair[804..808].try_into().unwrap()), 4);
            for v in &mut scene.palms {
                let Some(fixture) = &mut v.fixture else {
                    continue;
                };
                let index = (0..41)
                    .find(|i| {
                        (0..3).all(|axis| fixture.local[axis] == f(&mesh, 44 + i * 12 + axis * 4))
                    })
                    .unwrap();
                assert_eq!(fixture.weight, f32::from(mesh[632 + index * 4 + 3]) / 256.);
                fixture.modifiers[0][3] = f(pair, 8);
                fixture.modifiers[1][3] = f(pair, 808);
                let actual = fixture.local_position();
                for (axis, value) in actual.into_iter().enumerate() {
                    maximum =
                        maximum.max((value - f(pair, 800 + 212 + index * 12 + axis * 4)).abs());
                }
                checks += 1;
            }
        }
        assert_eq!(checks, 62 * 672);
        assert!(maximum < 1e-6, "local error {maximum}");
        println!("Fixture replay: {checks} corners, max local error {maximum}");
    }
    #[test]
    fn phase_preserves_native_wrap_boundary() {
        let tau = std::f32::consts::TAU;
        assert_eq!(advance_phase(tau, 0., 0.01), tau);
        assert_eq!(
            advance_phase(0., -0.03, 0.008).to_bits(),
            6.275_985_7_f32.to_bits()
        );
        assert_eq!(
            advance_phase(0., 0.04, 0.008).to_bits(),
            0.009_6_f32.to_bits()
        );
    }
    #[test]
    #[ignore = "Requires local GOG modifier startup and clock events"]
    fn native_fixture_clock() {
        let data = std::fs::read(std::env::var("OPENJADE_FIXTURE_CLOCK").unwrap()).unwrap();
        assert!(!data.is_empty() && data.len().is_multiple_of(36));
        let mut phases = std::collections::HashMap::<u32, (f32, u32, usize)>::new();
        for row in data.as_chunks::<36>().0 {
            let word = |at| u32::from_le_bytes(row[at..at + 4].try_into().unwrap());
            let frame = word(0);
            let object = word(8);
            let flags = word(12);
            assert!(flags == 21 || flags == 4);
            let before = f32::from_bits(word(16));
            let after = word(20);
            let dt = f32::from_bits(word(24));
            assert!(dt.is_finite() && dt > 0. && dt <= 0.1);
            let previous = phases.entry(object).or_insert((0., frame, 0));
            assert_eq!(previous.0.to_bits(), before.to_bits());
            if previous.2 > 0 {
                assert_eq!(frame, previous.1 + 1);
            }
            let calculated = advance_phase(previous.0, if flags == 21 { -0.03 } else { 0.04 }, dt);
            assert_eq!(
                calculated.to_bits(),
                after,
                "phase mismatch at frame {frame}"
            );
            *previous = (calculated, frame, previous.2 + 1);
        }
        assert_eq!(phases.len(), 4);
        assert!(phases.values().all(|v| v.2 == 1201));
        println!("Native fixture clock: 4804 exact phase updates; four modifiers start from zero");
    }
}
