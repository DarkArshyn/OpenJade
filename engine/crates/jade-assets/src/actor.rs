//! Independent CPU skeleton evaluation for the source-derived Prince diagnostic.
use crate::invalid;
use std::io;
type Matrix = [[f32; 4]; 4];
struct Bone {
    parent: i32,
    local: Matrix,
}
struct Track {
    bone: usize,
    rotation: bool,
    keys: Vec<(f32, [f32; 4])>,
}
struct Influence {
    bone: usize,
    weight: f32,
    point: [f32; 3],
}
pub struct Actor {
    bones: Vec<Bone>,
    order: Vec<usize>,
    tracks: Vec<Track>,
    vertices: Vec<(usize, Vec<Influence>)>,
    rate: f32,
    duration: f32,
}
struct Reader<'a> {
    data: &'a [u8],
    at: usize,
}
impl Reader<'_> {
    fn u32(&mut self) -> io::Result<u32> {
        let bytes = self
            .data
            .get(self.at..self.at + 4)
            .ok_or_else(|| invalid("Truncated actor"))?;
        self.at += 4;
        Ok(u32::from_le_bytes(bytes.try_into().unwrap()))
    }
    fn float(&mut self) -> io::Result<f32> {
        let f = f32::from_bits(self.u32()?);
        if !f.is_finite() {
            return Err(invalid("Nonfinite actor value"));
        }
        Ok(f)
    }
}
fn multiply(a: Matrix, b: Matrix) -> Matrix {
    std::array::from_fn(|i| std::array::from_fn(|j| (0..4).map(|k| a[i][k] * b[k][j]).sum()))
}
fn quaternion([x, y, z, w]: [f32; 4]) -> [[f32; 3]; 3] {
    [
        [
            1. - 2. * y * y - 2. * z * z,
            2. * x * y + 2. * w * z,
            2. * x * z - 2. * w * y,
        ],
        [
            2. * x * y - 2. * w * z,
            1. - 2. * x * x - 2. * z * z,
            2. * y * z + 2. * w * x,
        ],
        [
            2. * x * z + 2. * w * y,
            2. * y * z - 2. * w * x,
            1. - 2. * x * x - 2. * y * y,
        ],
    ]
}
fn slerp(a: [f32; 4], mut b: [f32; 4], t: f32) -> [f32; 4] {
    let mut dot = (0..4).map(|i| a[i] * b[i]).sum::<f32>();
    if dot < 0. {
        b = b.map(|x| -x);
        dot = -dot;
    }
    dot = dot.min(1.);
    if (dot - 1.).abs() <= 1.00000001e-7 {
        return a;
    }
    let angle = dot.acos();
    let mut q = std::array::from_fn::<_, 4, _>(|i| {
        ((1. - t) * angle).sin() * a[i] + (t * angle).sin() * b[i]
    });
    let norm = q.iter().map(|x| x * x).sum::<f32>().sqrt();
    q = q.map(|x| x / norm);
    q
}
impl Track {
    fn sample(&self, t: f32) -> [f32; 4] {
        let last = self.keys.last().unwrap();
        if t >= last.0 {
            return last.1;
        }
        let i = self.keys.partition_point(|k| k.0 <= t).saturating_sub(1);
        let (at, a) = self.keys[i];
        let (bt, b) = self.keys[i + 1];
        let f = (t - at) / (bt - at);
        if self.rotation {
            slerp(a, b, f)
        } else {
            std::array::from_fn(|j| a[j] + (b[j] - a[j]) * f)
        }
    }
}
impl Actor {
    pub fn decode(data: &[u8], vertex_count: usize) -> io::Result<Self> {
        if data.get(..8) != Some(b"OJACT001") || data.len() > 32 * 1024 * 1024 {
            return Err(invalid("Invalid actor sidecar"));
        }
        let mut r = Reader { data, at: 8 };
        let nb = r.u32()? as usize;
        let nt = r.u32()? as usize;
        let nv = r.u32()? as usize;
        let rate = r.float()?;
        let duration = r.float()?;
        if !(1..=256).contains(&nb)
            || nt > 512
            || nv != vertex_count
            || nv > 100000
            || !(0. < rate && rate <= 240.)
            || !(0. < duration && duration <= 100000.)
        {
            return Err(invalid("Invalid actor counts or timebase"));
        }
        let mut bones = Vec::new();
        for i in 0..nb {
            let parent = r.u32()? as i32;
            if parent < -1 || parent >= nb as i32 || parent == i as i32 {
                return Err(invalid("Invalid bone parent"));
            }
            let mut local = [[0.; 4]; 4];
            for row in &mut local {
                for value in row {
                    *value = r.float()?;
                }
            }
            if [local[0][3], local[1][3], local[2][3], local[3][3]] != [0., 0., 0., 1.] {
                return Err(invalid("Nonaffine bone"));
            }
            if local[3][..3].iter().any(|x| x.abs() > 10000.)
                || (0..3).any(|i| {
                    (0..3).any(|j| {
                        let dot = (0..3).map(|k| local[i][k] * local[j][k]).sum::<f32>();
                        (dot - if i == j { 1. } else { 0. }).abs() > 0.01
                    })
                })
            {
                return Err(invalid("Unsupported bone scale or translation"));
            }
            bones.push(Bone { parent, local });
        }
        let mut order = Vec::new();
        let mut done = vec![false; nb];
        while order.len() < nb {
            let previous = order.len();
            for i in 0..nb {
                let p = bones[i].parent;
                if !done[i] && (p < 0 || done[p as usize]) {
                    order.push(i);
                    done[i] = true;
                }
            }
            if previous == order.len() {
                return Err(invalid("Cyclic skeleton"));
            }
        }
        let mut tracks = Vec::new();
        let mut channels = std::collections::HashSet::new();
        for _ in 0..nt {
            let bone = r.u32()? as usize;
            let kind = r.u32()?;
            let n = r.u32()? as usize;
            if bone >= nb || kind > 1 || !(1..=10000).contains(&n) || !channels.insert((bone, kind))
            {
                return Err(invalid("Invalid animation channel"));
            }
            let mut keys = Vec::new();
            let mut previous = -1.;
            for i in 0..n {
                let tick = r.float()?;
                let mut q = [0.; 4];
                for v in &mut q {
                    *v = r.float()?;
                }
                let norm = q.iter().map(|x| x * x).sum::<f32>();
                if kind == 1 && q[..3].iter().any(|x| x.abs() > 10000.) {
                    return Err(invalid("Unbounded translation key"));
                }
                if tick <= previous
                    || tick > duration
                    || (i == 0 && tick != 0.)
                    || (kind == 0 && !(0.9..=1.1).contains(&norm))
                {
                    return Err(invalid("Invalid animation key"));
                }
                previous = tick;
                keys.push((tick, q));
            }
            tracks.push(Track {
                bone,
                rotation: kind == 0,
                keys,
            });
        }
        let mut vertices = Vec::new();
        let mut seen = vec![false; nv];
        for _ in 0..nv {
            let index = r.u32()? as usize;
            let n = r.u32()? as usize;
            if index >= nv || seen[index] || !(1..=3).contains(&n) {
                return Err(invalid("Invalid actor vertex binding"));
            }
            seen[index] = true;
            let mut weights = Vec::new();
            let mut total = 0.;
            for _ in 0..n {
                let bone = r.u32()? as usize;
                let weight = r.float()?;
                let point = [r.float()?, r.float()?, r.float()?];
                if bone >= nb
                    || !(0. < weight && weight <= 1.01)
                    || point.iter().any(|x| x.abs() > 10000.)
                {
                    return Err(invalid("Invalid skin influence"));
                }
                total += weight;
                weights.push(Influence {
                    bone,
                    weight,
                    point,
                });
            }
            if !(0.9..=1.1).contains(&total) {
                return Err(invalid("Invalid skin weight total"));
            }
            vertices.push((index, weights));
        }
        if r.at != data.len() {
            return Err(invalid("Trailing actor bytes"));
        }
        Ok(Self {
            bones,
            order,
            tracks,
            vertices,
            rate,
            duration,
        })
    }
    pub fn positions(&self, seconds: f64) -> Vec<(usize, [f32; 3])> {
        // Repeating this selected clip is a diagnostic policy, not a recovered action state machine.
        let tick = if seconds.is_finite() && seconds >= 0. {
            (seconds * f64::from(self.rate)).rem_euclid(f64::from(self.duration)) as f32
        } else {
            0.
        };
        let mut local: Vec<_> = self.bones.iter().map(|b| b.local).collect();
        for t in &self.tracks {
            let q = t.sample(tick);
            if t.rotation {
                let matrix = quaternion(q);
                for (row, v) in matrix.iter().enumerate() {
                    local[t.bone][row][..3].copy_from_slice(v);
                }
            } else {
                local[t.bone][3][..3].copy_from_slice(&q[..3]);
            }
        }
        let mut world = local.clone();
        for &i in &self.order {
            let p = self.bones[i].parent;
            world[i] = if p < 0 {
                local[i]
            } else {
                multiply(local[i], world[p as usize])
            };
        }
        self.vertices
            .iter()
            .map(|(index, weights)| {
                let mut xyz = [0.; 3];
                for w in weights {
                    let m = world[w.bone];
                    for (j, v) in xyz.iter_mut().enumerate() {
                        *v += w.weight
                            * (m[3][j] + (0..3).map(|k| w.point[k] * m[k][j]).sum::<f32>());
                    }
                }
                (*index, xyz)
            })
            .collect()
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<u8> {
        let mut b = b"OJACT001".to_vec();
        for n in [2u32, 1, 1] {
            b.extend(n.to_le_bytes());
        }
        for f in [1f32, 2.] {
            b.extend(f.to_le_bytes());
        }
        for (parent, xyz) in [(1i32, [0., 1., 0.]), (-1, [10., 0., 0.])] {
            b.extend(parent.to_le_bytes());
            for row in 0..4 {
                for col in 0..4 {
                    let value: f32 = if row == 3 && col < 3 {
                        xyz[col]
                    } else if row == col {
                        1.
                    } else {
                        0.
                    };
                    b.extend(value.to_le_bytes());
                }
            }
        }
        for n in [1u32, 1, 2] {
            b.extend(n.to_le_bytes());
        }
        for key in [[0f32, 10., 0., 0., 0.], [1., 20., 0., 0., 0.]] {
            for f in key {
                b.extend(f.to_le_bytes());
            }
        }
        for n in [0u32, 1, 0] {
            b.extend(n.to_le_bytes());
        }
        for f in [1f32, 0., 0., 0.] {
            b.extend(f.to_le_bytes());
        }
        b
    }
    #[test]
    fn hierarchy_interpolation_and_absolute_clock() {
        let actor = Actor::decode(&fixture(), 1).unwrap();
        assert_eq!(actor.positions(0.)[0].1, [10., 1., 0.]);
        assert_eq!(actor.positions(0.5)[0].1, [15., 1., 0.]);
        assert_eq!(actor.positions(1.5)[0].1, [20., 1., 0.]);
        assert_eq!(actor.positions(2.), actor.positions(0.));
        assert_eq!(actor.positions(0.5), actor.positions(0.5));
    }
    #[test]
    fn rejects_cycles_truncation_and_trailing_data() {
        let mut data = fixture();
        for n in 0..data.len() {
            assert!(Actor::decode(&data[..n], 1).is_err());
        }
        assert!(Actor::decode(&data, 2).is_err());
        data.extend([0]);
        assert!(Actor::decode(&data, 1).is_err());
        data.pop();
        data[96..100].copy_from_slice(&0u32.to_le_bytes());
        assert!(Actor::decode(&data, 1).is_err());
    }
    #[test]
    #[ignore = "Requires the local source-derived Prince sidecar and Python reference poses"]
    fn source_pose_parity() {
        let path = std::path::PathBuf::from(std::env::var("OPENJADE_ACTOR_FIXTURE").unwrap());
        let data = std::fs::read(path.with_extension("actor")).unwrap();
        let count = u32::from_le_bytes(data[16..20].try_into().unwrap()) as usize;
        let actor = Actor::decode(&data, count).unwrap();
        let bytes = std::fs::read(path.with_extension("poses")).unwrap();
        let mut r = Reader {
            data: &bytes,
            at: 0,
        };
        let frames = r.u32().unwrap();
        let mut maximum = 0f32;
        for _ in 0..frames {
            let time = r.float().unwrap();
            let positions = actor.positions(time as f64);
            for (index, p) in positions {
                assert!(index < count);
                for value in p {
                    maximum = maximum.max((value - r.float().unwrap()).abs());
                }
            }
        }
        assert_eq!(r.at, bytes.len());
        assert!(maximum < 2e-5, "position error {maximum}");
        println!("Prince Rust/Python maximum position difference: {maximum}");
    }
    #[test]
    fn row_composition() {
        let mut a = [[0.; 4]; 4];
        for (i, row) in a.iter_mut().enumerate() {
            row[i] = 1.;
        }
        let mut b = a;
        a[3][0] = 2.;
        b[3][1] = 3.;
        assert_eq!(multiply(a, b)[3], [2., 3., 0., 1.]);
    }
    #[test]
    fn quaternion_shortest_path() {
        let a = [0., 0., 0., 1.];
        assert_eq!(slerp(a, [0., 0., 0., -1.], 0.5), a);
        let q = slerp(a, [0., 0., 1., 0.], 0.5);
        let m = quaternion(q);
        assert!(m[0][0].abs() < 1e-6);
        assert!((m[0][1] - 1.).abs() < 1e-6);
    }
    #[test]
    fn truncated_rejected() {
        for n in 0..40 {
            assert!(Actor::decode(&vec![0; n], 1).is_err());
        }
    }
}
