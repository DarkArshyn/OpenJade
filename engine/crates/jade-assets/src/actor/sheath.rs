//! Bounded sheathed-dagger diagnostic, specified from original resources and measurements.
use super::{invalid, multiply, Matrix, Reader};
use std::io;
type V = [f32; 3];
fn dot(a: V, b: V) -> f32 {
    (0..3).map(|i| a[i] * b[i]).sum()
}
fn add(a: V, b: V) -> V {
    std::array::from_fn(|i| a[i] + b[i])
}
fn scale(a: V, s: f32) -> V {
    a.map(|x| x * s)
}
fn norm(a: V) -> V {
    scale(a, 1. / dot(a, a).sqrt().max(1e-20))
}
fn cross(a: V, b: V) -> V {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
fn project(a: V, n: V) -> V {
    add(a, scale(n, -dot(a, n)))
}
fn inverse_rotate(v: V, m: Matrix) -> V {
    std::array::from_fn(|i| dot(v, [m[i][0], m[i][1], m[i][2]]))
}
fn rotate(v: V, m: Matrix) -> V {
    std::array::from_fn(|j| (0..3).map(|i| v[i] * m[i][j]).sum())
}
pub(super) struct Sheath {
    pub bone: usize,
    length: f32,
    inertia: f32,
    response: f32,
    gravity: V,
    initial: V,
    planes: [[V; 4]; 2],
}
pub(super) struct State {
    point: V,
    velocity: V,
    previous: V,
}
impl Sheath {
    pub fn decode(data: &[u8], bones: usize) -> io::Result<Self> {
        if data.len() != 144 || &data[..8] != b"OJSHT001" {
            return Err(invalid("Invalid sheath sidecar"));
        }
        let mut r = Reader { data, at: 8 };
        let bone = r.u32()? as usize;
        let length = r.float()?;
        let inertia = r.float()?;
        let response = r.float()?;
        let mut vec = || -> io::Result<V> { Ok([r.float()?, r.float()?, r.float()?]) };
        let gravity = vec()?;
        let initial = vec()?;
        let mut planes = [[[0.; 3]; 4]; 2];
        for c in &mut planes {
            for v in c {
                *v = vec()?;
            }
        }
        if bone >= bones
            || !(0.0001..10.).contains(&length)
            || !(0.0..=1.).contains(&inertia)
            || !(0.0..=1.).contains(&response)
            || gravity.iter().any(|x| x.abs() > 100.)
            || (dot(initial, initial).sqrt() - length).abs() > 1e-5
            || planes
                .iter()
                .flatten()
                .any(|v| (dot(*v, *v) - 1.).abs() > 1e-4)
        {
            return Err(invalid("Unsupported sheath parameters"));
        }
        if planes
            .iter()
            .any(|c| dot(c[2], c[1]).abs() < 1e-4 || dot(c[3], c[0]).abs() < 1e-4)
        {
            return Err(invalid("Degenerate sheath constraint"));
        }
        Ok(Self {
            bone,
            length,
            inertia,
            response,
            gravity,
            initial,
            planes,
        })
    }
    pub fn initial(&self, parent: Matrix) -> State {
        State {
            point: self.initial,
            velocity: [0.; 3],
            previous: [parent[3][0], parent[3][1], parent[3][2]],
        }
    }
    pub fn step(&self, s: &mut State, parent: Matrix, dt: f32) {
        let origin = [parent[3][0], parent[3][1], parent[3][2]];
        let direction = norm(s.point);
        let delta = inverse_rotate(add(s.previous, scale(origin, -1.)), parent);
        let mut v = add(
            s.velocity,
            add(
                scale(project(delta, direction), self.inertia / dt),
                scale(inverse_rotate(self.gravity, parent), dt),
            ),
        );
        for &[a, b, soft_b, soft_a] in &self.planes {
            if dot(b, direction) < 0. {
                if dot(v, b) < 0. {
                    v = project(v, b);
                }
                if dot(a, direction) < 0. && dot(v, a) < 0. {
                    v = project(v, a);
                }
            } else if dot(a, direction) < 0. {
                if dot(v, a) < 0. {
                    v = project(v, a);
                }
            } else if dot(soft_b, direction) < 0. {
                if dot(v, soft_b) < 0. {
                    let f = -dot(soft_b, direction) / dot(soft_b, b).abs();
                    v = add(project(v, b), scale(b, f * dot(v, b)));
                }
            } else if dot(soft_a, direction) < 0. && dot(v, soft_a) < 0. {
                let f = -dot(soft_a, direction) / dot(soft_a, a).abs();
                v = add(project(v, a), scale(a, f * dot(v, a)));
            }
        }
        let p = add(s.point, scale(v, dt * self.response));
        let correction = scale(norm(p), dot(p, p).sqrt() - self.length);
        s.point = add(p, scale(correction, -1.));
        s.velocity = add(v, scale(correction, -1. / dt));
        s.previous = origin;
    }
    pub fn matrix(&self, s: &State, rest: Matrix, parent: Matrix) -> Matrix {
        let mut base = multiply(rest, parent);
        let target = norm(scale(rotate(s.point, parent), -1.));
        let axis = cross(target, [base[0][0], base[0][1], base[0][2]]);
        let sine = dot(axis, axis).sqrt().min(1.);
        if sine > 1e-8 {
            let n = norm(axis);
            let cosine = (1. - sine * sine).max(0.).sqrt();
            for row in base.iter_mut().take(3) {
                let v = [row[0], row[1], row[2]];
                let rotated = add(
                    add(scale(v, cosine), scale(cross(v, n), sine)),
                    scale(n, dot(v, n) * (1. - cosine)),
                );
                row[..3].copy_from_slice(&rotated);
            }
        }
        let p = add(
            rotate(s.point, parent),
            [parent[3][0], parent[3][1], parent[3][2]],
        );
        base[3][..3].copy_from_slice(&p);
        base
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<u8> {
        let mut data = b"OJSHT001".to_vec();
        data.extend(0u32.to_le_bytes());
        for value in [1f32, 0.5, 0.5, 0., 0., -10., 1., 0., 0.] {
            data.extend(value.to_le_bytes());
        }
        for _ in 0..8 {
            for value in [1f32, 0., 0.] {
                data.extend(value.to_le_bytes());
            }
        }
        data
    }
    #[test]
    fn gravity_preserves_length_and_constraints_are_bounded() {
        let data = fixture();
        let c = Sheath::decode(&data, 2).unwrap();
        let parent = std::array::from_fn(|i| std::array::from_fn(|j| if i == j { 1. } else { 0. }));
        let mut state = c.initial(parent);
        for _ in 0..100 {
            c.step(&mut state, parent, 0.008);
            assert!((dot(state.point, state.point) - 1.).abs() < 1e-5);
            assert!(state.velocity.iter().all(|v| v.is_finite()));
        }
        assert!(state.point[2] < -0.01);
        for n in 0..data.len() {
            assert!(Sheath::decode(&data[..n], 2).is_err());
        }
        let mut bad = data.clone();
        bad[8..12].copy_from_slice(&2u32.to_le_bytes());
        assert!(Sheath::decode(&bad, 2).is_err());
        let mut bad = data.clone();
        bad[12..16].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(Sheath::decode(&bad, 2).is_err());
        let mut bad = data.clone();
        bad[48 + 24..48 + 36].fill(0);
        bad[48 + 28..48 + 32].copy_from_slice(&1f32.to_le_bytes());
        assert!(Sheath::decode(&bad, 2).is_err());
    }
}
