//! Animated-normal lighting and the measured menu camera-relative contribution.
use super::{invalid, Actor, Matrix, Reader};
use std::io;

/// Diagnostic controls for the generated light, independent of named scene lights.
#[derive(Clone, Copy, Debug, Default)]
pub enum GeneratedLight {
    #[default]
    Dynamic,
    Frozen,
    Disabled,
}

/// World direction for the measured positive-polar-angle menu configuration.
/// Degenerate or nonfinite inputs are unsupported and retain the captured term.
pub fn generated_direction(owner: [f32; 3], camera: [f32; 3]) -> Option<[f32; 3]> {
    if !owner.into_iter().chain(camera).all(f32::is_finite) {
        return None;
    }
    let x = f64::from(owner[0]) - f64::from(camera[0]);
    let y = f64::from(owner[1]) - f64::from(camera[1]);
    if x.hypot(y) <= 1e-12 {
        return None;
    }
    // Parameters independently measured in the GOG executable and transition capture.
    let azimuth = y.atan2(x) + f64::from(std::f32::consts::PI);
    let polar = f64::from(0.3_f32);
    Some([
        (polar.sin() * azimuth.cos()) as f32,
        (polar.sin() * azimuth.sin()) as f32,
        polar.cos() as f32,
    ])
}

pub(super) struct Lighting {
    values: [f32; 31],
    pub(super) normals: Vec<Option<Vec<[f32; 3]>>>,
}
fn dot(a: [f32; 3], b: [f32; 3]) -> f32 {
    (0..3).map(|i| a[i] * b[i]).sum()
}
impl Lighting {
    pub fn decode(data: &[u8], actor: &Actor) -> io::Result<Self> {
        if data.get(..8) != Some(b"OJALIT01") || data.len() > 8 * 1024 * 1024 {
            return Err(invalid("Invalid actor lighting"));
        }
        let mut r = Reader { data, at: 8 };
        if r.u32()? as usize != actor.vertices.len() {
            return Err(invalid("Actor lighting count"));
        }
        let mut values = [0.; 31];
        for x in &mut values {
            *x = r.float()?;
            if x.abs() > 10000. {
                return Err(invalid("Actor light range"));
            }
        }
        for off in [0, 6, 12, 18, 26] {
            if values[off..off + 3]
                .iter()
                .any(|x| !(0.0..=4.0).contains(x))
            {
                return Err(invalid("Invalid actor light color"));
            }
        }
        for off in [3, 9] {
            let d = [values[off], values[off + 1], values[off + 2]];
            if (dot(d, d) - 1.).abs() > 1e-4 {
                return Err(invalid("Invalid light direction"));
            }
        }
        for off in [21, 29] {
            if values[off] < 0. || values[off + 1] < 0. {
                return Err(invalid("Invalid light attenuation"));
            }
        }
        let mut normals = Vec::new();
        for (_, weights) in &actor.vertices {
            match r.u32()? {
                0 => normals.push(None),
                1 => {
                    let mut ns = Vec::new();
                    for _ in weights {
                        let v = [r.float()?, r.float()?, r.float()?];
                        if dot(v, v) > 100. {
                            return Err(invalid("Actor normal range"));
                        }
                        ns.push(v);
                    }
                    normals.push(Some(ns));
                }
                _ => return Err(invalid("Actor lighting mode")),
            }
        }
        if r.at != data.len() {
            return Err(invalid("Trailing actor lighting"));
        }
        Ok(Self { values, normals })
    }
    pub fn colors(
        &self,
        actor: &Actor,
        world: &[Matrix],
        positions: &[(usize, [f32; 3])],
        generated: &[Option<[f32; 3]>],
        mode: GeneratedLight,
    ) -> Vec<Option<[f32; 3]>> {
        let mut values = self.values;
        if matches!(mode, GeneratedLight::Disabled) {
            values[12..15].fill(0.);
        }
        let c = &values;
        actor
            .vertices
            .iter()
            .zip(&self.normals)
            .zip(positions)
            .enumerate()
            .map(|(index, (((_, weights), normals), (_, p)))| {
                let ns = normals.as_ref()?;
                let mut n = [0.; 3];
                for (w, v) in weights.iter().zip(ns) {
                    for (j, x) in n.iter_mut().enumerate() {
                        *x += w.weight * (0..3).map(|i| v[i] * world[w.bone][i][j]).sum::<f32>();
                    }
                }
                let length = dot(n, n).sqrt();
                if length <= 1e-12 {
                    return Some([c[0], c[1], c[2]]);
                }
                n = n.map(|x| x / length);
                let mut rgb = [c[0], c[1], c[2]];
                for off in [3, 9] {
                    let fallback = [c[off], c[off + 1], c[off + 2]];
                    let slot = actor.light_origins.as_ref().map_or(0, |o| o.slots[index]);
                    let d = if off == 9 {
                        generated.get(slot).copied().flatten().unwrap_or(fallback)
                    } else {
                        fallback
                    };
                    let factor = dot(n, d).max(0.);
                    for j in 0..3 {
                        rgb[j] += factor * c[off + 3 + j];
                    }
                }
                for off in [15, 23] {
                    let delta = std::array::from_fn(|j| c[off + j] - p[j]);
                    let distance = dot(delta, delta).sqrt();
                    let factor = if distance > 1e-12 {
                        (dot(n, delta) / distance).clamp(0., 1.)
                            * ((c[off + 6] - distance) * c[off + 7]).clamp(0., 1.)
                    } else {
                        0.
                    };
                    for j in 0..3 {
                        rgb[j] += factor * c[off + 3 + j];
                    }
                }
                Some(rgb.map(|x| x.clamp(0., 1.)))
            })
            .collect()
    }
}
