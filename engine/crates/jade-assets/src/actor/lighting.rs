//! Animated-normal lighting diagnostic; lighting inputs retain capture provenance.
use super::{invalid, Actor, Matrix, Reader};
use std::io;
pub(super) struct Lighting {
    values: [f32; 31],
    normals: Vec<Option<Vec<[f32; 3]>>>,
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
    ) -> Vec<Option<[f32; 3]>> {
        let c = &self.values;
        actor
            .vertices
            .iter()
            .zip(&self.normals)
            .zip(positions)
            .map(|(((_, weights), normals), (_, p))| {
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
                    let d = [c[off], c[off + 1], c[off + 2]];
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
