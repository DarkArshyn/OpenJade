//! Local-space rido2 cloth for the frozen PC menu.
use crate::{curtain_field::curtain_weight, invalid};
use std::io;

type Vec3 = [f32; 3];
pub struct Curtain {
    first: usize,
    ids: [u8; 96],
    matrix: [f32; 16],
    positions: [Vec3; 25],
    previous: [Vec3; 25],
    fixed: [bool; 25],
    uv: [[f32; 2]; 25],
    links: [(usize, usize, f32); 40],
    plane: Option<[f32; 4]>,
    wind: [Vec3; 2],
    ticks: u64,
    remainder: f64,
}
impl Curtain {
    pub fn decode(b: &[u8], vertices: &[f32]) -> io::Result<Self> {
        let legacy = b.starts_with(b"OJRIDO01") && b.len() == 1368;
        let has_plane = legacy || (b.starts_with(b"OJRIDO05") && b.len() == 1392);
        if !has_plane && !(b.starts_with(b"OJRIDO04") && b.len() == 1376) {
            return Err(invalid("Invalid rido2 data"));
        }
        let word = |o: usize| u32::from_le_bytes(b[o..o + 4].try_into().unwrap());
        let f = |o| f32::from_bits(word(o));
        let first = word(8) as usize;
        let matrix = std::array::from_fn(|i| f(12 + i * 4));
        let positions = std::array::from_fn(|i| std::array::from_fn(|k| f(76 + 12 * i + 4 * k)));
        let fixed = std::array::from_fn(|i| word(376 + 16 * i) == 1);
        let uv = std::array::from_fn(|i| [f(384 + 16 * i), f(388 + 16 * i)]);
        let links = std::array::from_fn(|i| {
            let o = 776 + 12 * i;
            (word(o) as usize, word(o + 4) as usize, f(o + 8))
        });
        let plane = has_plane.then(|| std::array::from_fn(|i| f(1256 + 4 * i)));
        let wind = if legacy {
            [[-1.5, 1., 0.], [-2., 3., 0.]]
        } else {
            let offset = if has_plane { 1272 } else { 1256 };
            std::array::from_fn(|j| std::array::from_fn(|k| f(offset + 12 * j + 4 * k)))
        };
        let ids: [u8; 96] = b[b.len() - 96..].try_into().unwrap();
        if first + 96 > vertices.len() / 9
            || ids.iter().any(|&i| i >= 25)
            || (0..25).any(|i| word(376 + 16 * i) > 1 || word(380 + 16 * i) != i as u32)
            || links.iter().any(|&(a, b, l)| {
                a >= 25 || b >= 25 || a == b || !(0.0..10.).contains(&l) || l == 0.
            })
            || matrix
                .iter()
                .chain(positions.iter().flatten())
                .chain(uv.iter().flatten())
                .chain(plane.iter().flatten())
                .chain(wind.iter().flatten())
                .any(|v| !v.is_finite() || v.abs() > 10000.)
        {
            return Err(invalid("Invalid rido2 controls"));
        }
        let cloth = Self {
            first,
            ids,
            matrix,
            positions,
            previous: positions,
            fixed,
            uv,
            links,
            plane,
            wind,
            ticks: 0,
            remainder: 0.,
        };
        for (i, xyz) in cloth.corners() {
            if (0..3).any(|k| (xyz[k] - vertices[i * 9 + k]).abs() > 0.0001) {
                return Err(invalid("rido2 does not match scene geometry"));
            }
        }
        Ok(cloth)
    }
    pub fn corners(&self) -> impl Iterator<Item = (usize, Vec3)> + '_ {
        self.ids.iter().enumerate().map(|(i, &id)| {
            let p = self.positions[id as usize];
            let xyz = std::array::from_fn(|k| {
                self.matrix[12 + k] + (0..3).map(|j| p[j] * self.matrix[4 * j + k]).sum::<f32>()
            });
            (self.first + i, xyz)
        })
    }
    pub fn advance(&mut self, seconds: f32) {
        self.remainder += f64::from(seconds) * 60.;
        while self.remainder + 1e-9 >= 1. {
            self.remainder -= 1.;
            self.step();
        }
    }
    fn collide(&mut self) {
        let Some(plane) = self.plane else {
            return;
        };
        for (p, &fixed) in self.positions.iter_mut().zip(&self.fixed) {
            if fixed {
                continue;
            }
            let distance = (0..3).map(|k| p[k] * plane[k]).sum::<f32>() - plane[3];
            if distance < 0. {
                for (k, x) in p.iter_mut().enumerate() {
                    *x -= distance * plane[k];
                }
            }
        }
    }
    fn step(&mut self) {
        let phase = (self.ticks % 25600) as f32 / 50.;
        self.ticks += 1;
        for i in 0..25 {
            if self.fixed[i] {
                continue;
            }
            let [u, v] = self.uv[i];
            let w = curtain_weight(0.8 * u + phase, 0.8 * v + phase);
            let mut acceleration: Vec3 =
                std::array::from_fn(|k| self.wind[0][k] + w * (self.wind[1][k] - self.wind[0][k]));
            acceleration[2] -= 5.;
            let p = self.positions[i];
            for k in 0..3 {
                self.positions[i][k] = 2. * p[k] - self.previous[i][k] + acceleration[k] / 3600.;
            }
            self.previous[i] = p;
        }
        for _ in 0..2 {
            self.collide();
            for _ in 0..2 {
                for &(a, b, rest) in &self.links {
                    let delta: Vec3 =
                        std::array::from_fn(|k| self.positions[b][k] - self.positions[a][k]);
                    let length = delta.iter().map(|x| x * x).sum::<f32>().sqrt();
                    if length == 0. {
                        continue;
                    }
                    let share = if self.fixed[a] || self.fixed[b] {
                        1.
                    } else {
                        0.5
                    };
                    for (k, d) in delta.into_iter().enumerate() {
                        let offset = d * ((length - rest) / length) * share;
                        if !self.fixed[a] {
                            self.positions[a][k] += offset;
                        }
                        if self.fixed[a] || !self.fixed[b] {
                            self.positions[b][k] -= offset;
                        }
                    }
                }
            }
        }
        self.collide();
    }
}
