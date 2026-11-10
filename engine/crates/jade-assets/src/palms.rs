//! Sparse local-space waves expressed in the scene's world basis.
use crate::invalid;
use std::{io, sync::OnceLock};

pub struct PalmVertex {
    pub(crate) fixture: Option<crate::fixtures::Fixture>,
    pub index: usize,
    base: [f32; 3],
    angles: [f32; 2],
    rate: f32,
    phase: f32,
    axes: [[f32; 3]; 2],
    quarter: usize,
}

pub(crate) fn wave(angle: f32, shift: usize) -> f32 {
    let index = (f64::from(angle) * f64::from(f32::from_bits(0x4322f983))).round_ties_even() as i64;
    sine_index((index as usize).wrapping_add(shift))
}
pub(crate) fn sine_index(index: usize) -> f32 {
    static TABLE: OnceLock<[f32; 1024]> = OnceLock::new();
    let table = TABLE.get_or_init(|| {
        std::array::from_fn(|i| (i as f64 * f64::from(std::f32::consts::TAU / 1024.)).sin() as f32)
    });
    table[index & 1023]
}

impl PalmVertex {
    pub(crate) fn fixture(index: usize, base: [f32; 3], fixture: crate::fixtures::Fixture) -> Self {
        Self {
            index,
            base,
            fixture: Some(fixture),
            angles: [0.; 2],
            rate: 0.,
            phase: 0.,
            axes: [[0.; 3]; 2],
            quarter: 0,
        }
    }

    pub fn advance(&mut self, dt: f32) {
        if let Some(fixture) = &mut self.fixture {
            fixture.advance(dt);
            return;
        }
        self.phase = (self.phase + self.rate * 30. * dt).rem_euclid(std::f32::consts::TAU);
    }
    pub fn position(&self) -> [f32; 3] {
        if let Some(fixture) = &self.fixture {
            return fixture.position(self.base);
        }
        let a = wave(self.angles[0] + self.phase, 0);
        let b = wave(self.angles[1] + self.phase, self.quarter);
        std::array::from_fn(|i| self.base[i] + a * self.axes[0][i] + b * self.axes[1][i])
    }
}

pub(crate) fn decode(bytes: &[u8], vertices: &[f32]) -> io::Result<Vec<PalmVertex>> {
    let mut result = Vec::new();
    let mut previous = None;
    for record in bytes.as_chunks::<44>().0 {
        let words = record.as_chunks::<4>().0;
        let index = u32::from_le_bytes(words[0]) as usize;
        let quarter = u32::from_le_bytes(words[1]);
        let values: [f32; 9] = std::array::from_fn(|i| f32::from_le_bytes(words[i + 2]));
        if index >= vertices.len() / 9
            || previous.is_some_and(|p| index <= p)
            || quarter > 1
            || values.iter().any(|v| !v.is_finite() || v.abs() > 10000.)
        {
            return Err(invalid("Invalid palm deformation record"));
        }
        previous = Some(index);
        result.push(PalmVertex {
            fixture: None,
            index,
            base: vertices[index * 9..index * 9 + 3].try_into().unwrap(),
            angles: [values[0], values[1]],
            rate: values[2],
            phase: 0.,
            axes: [
                [values[3], values[4], values[5]],
                [values[6], values[7], values[8]],
            ],
            quarter: quarter as usize * 256,
        });
    }
    Ok(result)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn table_matches_double_angle_reference() {
        let mut fingerprint = 0xcbf29ce484222325_u64;
        for i in 0..1024 {
            let radians = i as f32 * (std::f32::consts::TAU / 1024.);
            for byte in wave(radians, 0).to_le_bytes() {
                fingerprint = (fingerprint ^ u64::from(byte)).wrapping_mul(0x100000001b3);
            }
        }
        assert_eq!(fingerprint, 0xc9553a859f12e437);
    }
    #[test]
    fn signed_phase_and_local_axes() {
        let mut v = PalmVertex {
            fixture: None,
            index: 0,
            base: [4., 5., 6.],
            angles: [0.; 2],
            rate: -0.05,
            phase: 0.,
            axes: [[0., 0.1, 0.], [0., 0., 0.1]],
            quarter: 256,
        };
        assert_eq!(v.position(), [4., 5., 6.1]);
        v.advance(std::f32::consts::FRAC_PI_2 / 1.5);
        assert_eq!(v.position(), [4., 4.9, 6.]);
        assert_eq!(wave(-std::f32::consts::FRAC_PI_2, 0), -1.);
    }
}
