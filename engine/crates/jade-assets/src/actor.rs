//! Independent CPU skeleton evaluation for the source-derived Prince diagnostic.
use crate::invalid;
use std::io;
mod lighting;
pub use lighting::{generated_direction, GeneratedLight};
mod sheath;
pub type RenderVertex = (usize, [f32; 3], Option<[f32; 3]>);
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
struct LightOrigins {
    bones: Vec<Option<usize>>,
    slots: Vec<usize>,
}
pub struct Actor {
    light_origins: Option<LightOrigins>,
    placement: Option<(usize, Matrix)>,
    sheath: Option<sheath::Sheath>,
    sheath_states: Vec<sheath::State>,
    sheath_cursor: std::cell::RefCell<Option<(usize, sheath::State)>>,
    lighting: Option<lighting::Lighting>,
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
    if (dot - 1.).abs() <= 1e-7 {
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
            light_origins: None,
            placement: None,
            sheath: None,
            sheath_states: Vec::new(),
            sheath_cursor: std::cell::RefCell::new(None),
            lighting: None,
            bones,
            order,
            tracks,
            vertices,
            rate,
            duration,
        })
    }
    pub fn load_sheath(&mut self, data: &[u8]) -> io::Result<()> {
        let control = sheath::Sheath::decode(data, self.bones.len())?;
        if self.bones[control.bone].parent < 0 || self.duration / self.rate > 10. {
            return Err(invalid("Sheath requires parent"));
        }
        // Cache the first cycle; native controller state persists across body loops.
        // Cache only complete steps; the fractional step remains local to each query.
        // At most 1251 states (45,036 bytes) for the bounded ten-second clip.
        let parent = self.bones[control.bone].parent as usize;
        let mut state = control.initial(self.base_world(0.)[parent]);
        let steps = (f64::from(self.duration / self.rate) * 125.).floor() as usize;
        let mut states = Vec::with_capacity(steps + 1);
        states.push(state.clone());
        for step in 1..=steps {
            let pose = self.base_world(step as f64 / 125.);
            control.step(&mut state, pose[parent], 1. / 125.);
            states.push(state.clone());
        }
        self.sheath_states = states;
        *self.sheath_cursor.borrow_mut() = None;
        self.sheath = Some(control);
        Ok(())
    }
    fn base_world(&self, seconds: f64) -> Vec<Matrix> {
        // Repeating this selected clip is a diagnostic policy, not a recovered action state machine.
        let tick = if seconds.is_finite() && (0. ..=86400.).contains(&seconds) {
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
        world
    }
    fn evaluated_world(&self, seconds: f64) -> Vec<Matrix> {
        let mut world = self.base_world(seconds);
        if let Some(c) = &self.sheath {
            // Only the body clip wraps. Preserve controller history across its boundary.
            // Startup/action selection remains diagnostic; invalid clocks reset the query to zero.
            let time = if seconds.is_finite() && (0. ..=86400.).contains(&seconds) {
                seconds
            } else {
                0.
            };
            let parent = self.bones[c.bone].parent as usize;
            let steps = (time * 125.).floor() as usize;
            let first_cycle = steps.min(self.sheath_states.len() - 1);
            let cached = self.sheath_cursor.borrow().clone();
            let (from, mut state) = match cached {
                Some((at, state)) if at > first_cycle && at <= steps => (at, state),
                _ => (first_cycle, self.sheath_states[first_cycle].clone()),
            };
            for step in from + 1..=steps {
                let pose = self.base_world(step as f64 / 125.);
                c.step(&mut state, pose[parent], 1. / 125.);
            }
            // Never commit a fractional step: repeated timestamps and seeks remain deterministic.
            *self.sheath_cursor.borrow_mut() = Some((steps, state.clone()));
            let remaining = (time - steps as f64 / 125.) as f32;
            if remaining > 1e-7 {
                c.step(&mut state, world[parent], remaining);
            }
            world[c.bone] = c.matrix(&state, self.bones[c.bone].local, world[parent]);
            let mut changed = vec![false; self.bones.len()];
            changed[c.bone] = true;
            for &i in &self.order {
                let p = self.bones[i].parent;
                if i != c.bone && p >= 0 && changed[p as usize] {
                    world[i] = multiply(self.bones[i].local, world[p as usize]);
                    changed[i] = true;
                }
            }
        }
        world
    }
    #[cfg(test)]
    fn replayed_world(&self, seconds: f64) -> Vec<Matrix> {
        let mut world = self.base_world(seconds);
        if let Some(c) = &self.sheath {
            // Only the body clip wraps. Preserve controller history across its boundary.
            // Startup/action selection remains diagnostic; invalid clocks reset the query to zero.
            let time = if seconds.is_finite() && (0. ..=86400.).contains(&seconds) {
                seconds
            } else {
                0.
            };
            let parent = self.bones[c.bone].parent as usize;
            let first = self.base_world(0.);
            let mut state = c.initial(first[parent]);
            let steps = (time * 125.).floor() as usize;
            for step in 1..=steps {
                let pose = self.base_world(step as f64 / 125.);
                c.step(&mut state, pose[parent], 1. / 125.);
            }
            let remaining = (time - steps as f64 / 125.) as f32;
            if remaining > 1e-7 {
                c.step(&mut state, world[parent], remaining);
            }
            world[c.bone] = c.matrix(&state, self.bones[c.bone].local, world[parent]);
            let mut changed = vec![false; self.bones.len()];
            changed[c.bone] = true;
            for &i in &self.order {
                let p = self.bones[i].parent;
                if i != c.bone && p >= 0 && changed[p as usize] {
                    world[i] = multiply(self.bones[i].local, world[p as usize]);
                    changed[i] = true;
                }
            }
        }
        world
    }
    pub fn load_placement(&mut self, data: &[u8], scene_vertices: usize) -> io::Result<()> {
        if data.len() != 76 || &data[..8] != b"OJAPL001" {
            return Err(invalid("Invalid actor placement"));
        }
        let mut r = Reader { data, at: 8 };
        let offset = r.u32()? as usize;
        let mut m = [[0.; 4]; 4];
        for row in &mut m {
            for value in row {
                *value = r.float()?;
            }
        }
        if offset
            .checked_add(self.vertices.len())
            .is_none_or(|n| n > scene_vertices)
            || (0..3).any(|i| m[i][3] != 0. || m[3][i].abs() > 10000.)
            || m[3][3] != 1.
        {
            return Err(invalid("Invalid actor placement extent"));
        }
        for i in 0..3 {
            for j in 0..3 {
                let dot = (0..3).map(|k| m[i][k] * m[j][k]).sum::<f32>();
                if (dot - if i == j { 1. } else { 0. }).abs() > 1e-4 {
                    return Err(invalid("Nonrigid actor placement"));
                }
            }
        }
        self.placement = Some((offset, m));
        Ok(())
    }
    fn placed(&self, index: usize, p: [f32; 3]) -> (usize, [f32; 3]) {
        if let Some((offset, m)) = self.placement {
            (
                offset + index,
                std::array::from_fn(|j| m[3][j] + (0..3).map(|i| p[i] * m[i][j]).sum::<f32>()),
            )
        } else {
            (index, p)
        }
    }
    pub fn load_lighting(&mut self, data: &[u8]) -> io::Result<()> {
        self.lighting = Some(lighting::Lighting::decode(data, self)?);
        Ok(())
    }
    pub fn render_vertices(&self, seconds: f64) -> Vec<RenderVertex> {
        self.render_lit_vertices(seconds, None, GeneratedLight::Frozen)
    }
    /// Optional source-mapped receiver origins; older packages use the actor root.
    pub fn load_light_origins(&mut self, data: &[u8]) -> io::Result<()> {
        if data.get(..8) != Some(b"OJAORG01") || data.len() != 12 + 4 * self.vertices.len() {
            return Err(invalid("Invalid actor light origins"));
        }
        let mut reader = Reader { data, at: 8 };
        if reader.u32()? as usize != self.vertices.len() {
            return Err(invalid("Actor light origin count"));
        }
        let mut bones = vec![None];
        let mut slots = Vec::with_capacity(self.vertices.len());
        for _ in &self.vertices {
            let value = reader.u32()?;
            let bone = if value == u32::MAX {
                None
            } else {
                if value as usize >= self.bones.len() {
                    return Err(invalid("Actor light origin bone"));
                }
                Some(value as usize)
            };
            let slot = if let Some(at) = bones.iter().position(|b| *b == bone) {
                at
            } else {
                bones.push(bone);
                bones.len() - 1
            };
            slots.push(slot);
        }
        self.light_origins = Some(LightOrigins { bones, slots });
        Ok(())
    }
    /// Recompute the generated term only for actors with a world placement.
    pub fn render_vertices_for_camera(
        &self,
        seconds: f64,
        camera: [f32; 3],
        mode: GeneratedLight,
    ) -> Vec<RenderVertex> {
        self.render_lit_vertices(seconds, Some(camera), mode)
    }
    fn generated_directions(
        &self,
        world: &[Matrix],
        camera: Option<[f32; 3]>,
        mode: GeneratedLight,
    ) -> Vec<Option<[f32; 3]>> {
        let Some((_, matrix)) = self.placement else {
            return vec![None];
        };
        let Some(camera) = camera else {
            return vec![None];
        };
        if !matches!(mode, GeneratedLight::Dynamic) {
            return vec![None];
        }
        let bones = self
            .light_origins
            .as_ref()
            .map_or(&[None][..], |o| o.bones.as_slice());
        bones
            .iter()
            .map(|bone| {
                let local = bone.map_or([0.; 3], |i| world[i][3][..3].try_into().unwrap());
                let origin = std::array::from_fn(|j| {
                    matrix[3][j] + (0..3).map(|i| local[i] * matrix[i][j]).sum::<f32>()
                });
                generated_direction(origin, camera).map(|direction| {
                    let local: [f32; 3] =
                        std::array::from_fn(|i| (0..3).map(|j| direction[j] * matrix[i][j]).sum());
                    let length = local.iter().map(|x| x * x).sum::<f32>().sqrt();
                    local.map(|x| x / length)
                })
            })
            .collect()
    }
    fn render_lit_vertices(
        &self,
        seconds: f64,
        camera: Option<[f32; 3]>,
        mode: GeneratedLight,
    ) -> Vec<RenderVertex> {
        let world = self.evaluated_world(seconds);
        let positions = self.skin_positions(&world);
        let generated = self.generated_directions(&world, camera, mode);
        let colors = self
            .lighting
            .as_ref()
            .map(|l| l.colors(self, &world, &positions, &generated, mode));
        positions
            .into_iter()
            .enumerate()
            .map(|(i, (index, p))| {
                let (index, p) = self.placed(index, p);
                (index, p, colors.as_ref().and_then(|c| c[i]))
            })
            .collect()
    }
    pub fn has_reflection_normals(&self, first: usize, count: usize) -> bool {
        let Some(light) = &self.lighting else {
            return false;
        };
        let offset = self.placement.map_or(0, |p| p.0);
        let mut found = 0;
        for ((index, _), normals) in self.vertices.iter().zip(&light.normals) {
            if (*index + offset) >= first && (*index + offset) < first.saturating_add(count) {
                if normals.is_none() {
                    return false;
                }
                found += 1;
            }
        }
        found == count
    }
    /// Unnormalized animated normals projected with the measured native UV rule.
    pub fn reflection_uvs(
        &self,
        seconds: f64,
        first: usize,
        count: usize,
        right: [f32; 3],
        up: [f32; 3],
    ) -> Vec<(usize, [f32; 2])> {
        let Some(light) = &self.lighting else {
            return Vec::new();
        };
        let world = self.evaluated_world(seconds);
        let offset = self.placement.map_or(0, |p| p.0);
        self.vertices
            .iter()
            .zip(&light.normals)
            .filter_map(|((index, weights), normals)| {
                let index = index + offset;
                if index < first || index >= first.saturating_add(count) {
                    return None;
                }
                let normals = normals.as_ref()?;
                let mut n = [0.; 3];
                for (w, normal) in weights.iter().zip(normals) {
                    for (j, v) in n.iter_mut().enumerate() {
                        *v +=
                            w.weight * (0..3).map(|i| normal[i] * world[w.bone][i][j]).sum::<f32>();
                    }
                }
                if let Some((_, matrix)) = self.placement {
                    n = std::array::from_fn(|j| (0..3).map(|i| n[i] * matrix[i][j]).sum());
                }
                // Native view Y is downward; renderer camera.up points upward.
                let u = 0.5 - 0.5 * (0..3).map(|i| right[i] * n[i]).sum::<f32>();
                let v = 0.5 + 0.5 * (0..3).map(|i| up[i] * n[i]).sum::<f32>();
                Some((index, [u, v]))
            })
            .collect()
    }
    pub fn positions(&self, seconds: f64) -> Vec<(usize, [f32; 3])> {
        self.skin_positions(&self.evaluated_world(seconds))
    }
    fn skin_positions(&self, world: &[Matrix]) -> Vec<(usize, [f32; 3])> {
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
    #[test]
    fn placement_is_rigid_bounded_and_does_not_change_local_lighting_space() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
        let mut data = b"OJAPL001".to_vec();
        data.extend(4u32.to_le_bytes());
        for row in 0..4 {
            for col in 0..4 {
                let value: f32 = if row == 3 && col == 0 {
                    100.
                } else if row == col {
                    1.
                } else {
                    0.
                };
                data.extend(value.to_le_bytes());
            }
        }
        actor.load_placement(&data, 5).unwrap();
        assert_eq!(actor.render_vertices(0.)[0], (4, [110., 1., 0.], None));
        assert_eq!(actor.positions(0.)[0], (0, [10., 1., 0.]));
        assert!(actor.load_placement(&data, 4).is_err());
        for n in 0..data.len() {
            assert!(actor.load_placement(&data[..n], 5).is_err());
        }
        data[12..16].copy_from_slice(&2f32.to_le_bytes());
        assert!(actor.load_placement(&data, 5).is_err());
    }
    #[test]
    #[ignore = "Requires the private grounded balcony scene"]
    fn source_grounded_balcony_upload() {
        let path = std::path::PathBuf::from(std::env::var("OPENJADE_BALCONY_SCENE").unwrap());
        let scene = crate::Scene::load(&path).unwrap();
        let actor = scene.actor.as_ref().unwrap();
        let (offset, _) = actor.placement.unwrap();
        // Independent native-contact reference for this private fixture, not a runtime constant.
        let native_z = 1.3420553f32;
        for time in [0., 2., 3.99999, 4., 8.01] {
            let local = actor.positions(time);
            let uploaded = actor.render_vertices(time);
            for ((index, xyz), (target, world, _)) in local.iter().zip(uploaded) {
                assert_eq!(target, offset + index);
                assert!(target < scene.vertices.len() / 9);
                assert!((world[2] - (xyz[2] + native_z)).abs() < 1e-6);
            }
        }
    }
    fn check_replay(actor: &Actor) {
        // Out-of-order seeks, loop boundaries and fractional steps must stay identical.
        for time in [
            3.99999,
            0.001,
            2.,
            4.,
            8.003,
            0.008,
            0.007999,
            0.,
            -1.,
            f64::NAN,
            f64::INFINITY,
            f64::MAX,
        ]
        .into_iter()
        .chain((0..53).rev().map(|i| i as f64 * 0.07913))
        {
            assert_eq!(
                actor.evaluated_world(time),
                actor.replayed_world(time),
                "time={time}"
            );
        }
    }
    #[test]
    fn cached_sheath_preserves_replay_and_reload() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
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
        actor.load_sheath(&data).unwrap();
        check_replay(&actor);
        assert_ne!(actor.positions(0.), actor.positions(4.));
        let before = actor.positions(0.57);
        assert!(actor.load_sheath(&data[..100]).is_err());
        assert_eq!(before, actor.positions(0.57));
        data[32..36].copy_from_slice(&(-5f32).to_le_bytes());
        actor.load_sheath(&data).unwrap();
        check_replay(&actor);
        assert_ne!(before, actor.positions(0.57));
    }
    #[test]
    #[ignore = "Requires the private actor sheath fixture"]
    fn source_cached_sheath_matches_replay() {
        let path = std::path::PathBuf::from(std::env::var("OPENJADE_ACTOR_FIXTURE").unwrap());
        let data = std::fs::read(&path).unwrap();
        let count = u32::from_le_bytes(data[16..20].try_into().unwrap()) as usize;
        let mut actor = Actor::decode(&data, count).unwrap();
        actor
            .load_sheath(&std::fs::read(path.with_extension("sheath")).unwrap())
            .unwrap();
        check_replay(&actor);
        let before = actor.positions(3.99999);
        let after = actor.positions(4.);
        for ((_, a), (_, b)) in before.iter().zip(after) {
            assert!((0..3).map(|j| (a[j] - b[j]).powi(2)).sum::<f32>().sqrt() < 1e-4);
        }
    }
    fn lighting_fixture(active: u32) -> Vec<u8> {
        let mut data = b"OJALIT01".to_vec();
        data.extend(1u32.to_le_bytes());
        let mut values = [0f32; 31];
        values[0] = 0.1;
        values[3] = 1.;
        values[6] = 0.5;
        values[9] = 1.;
        for value in values {
            data.extend(value.to_le_bytes());
        }
        data.extend(active.to_le_bytes());
        if active == 1 {
            for v in [1f32, 0., 0.] {
                data.extend(v.to_le_bytes());
            }
        }
        data
    }
    #[test]
    fn reflection_retains_normal_length_and_uses_upward_camera_convention() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
        actor.load_lighting(&lighting_fixture(1)).unwrap();
        assert!(actor.has_reflection_normals(0, 1));
        assert!(!actor.has_reflection_normals(0, 2));
        let uvs = actor.reflection_uvs(0., 0, 1, [1., 0., 0.], [1., 0., 0.]);
        assert_eq!(uvs, vec![(0, [0., 1.])]);
        actor.lighting.as_mut().unwrap().normals[0] = Some(vec![[2., 0., 0.]]);
        assert_eq!(
            actor.reflection_uvs(0., 0, 1, [1., 0., 0.], [1., 0., 0.]),
            vec![(0, [-0.5, 1.5])]
        );
        actor.load_lighting(&lighting_fixture(0)).unwrap();
        assert!(!actor.has_reflection_normals(0, 1));
    }
    #[test]
    fn animated_normals_change_light_and_fixed_material_keeps_its_color() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
        let data = lighting_fixture(1);
        actor.load_lighting(&data).unwrap();
        assert_eq!(actor.render_vertices(0.)[0].2, Some([0.6, 0., 0.]));
        actor.bones[0].local[0][0] = -1.;
        actor.bones[0].local[1][1] = -1.;
        assert_eq!(actor.render_vertices(0.)[0].2, Some([0.1, 0., 0.]));
        for n in 0..data.len() {
            assert!(actor.load_lighting(&data[..n]).is_err());
        }
        actor.load_lighting(&lighting_fixture(0)).unwrap();
        assert_eq!(actor.render_vertices(0.)[0].2, None);
    }
    #[test]
    #[ignore = "Requires the private actor lighting fixture"]
    fn source_lighting_parity() {
        let path = std::path::PathBuf::from(std::env::var("OPENJADE_ACTOR_FIXTURE").unwrap());
        let data = std::fs::read(&path).unwrap();
        let count = u32::from_le_bytes(data[16..20].try_into().unwrap()) as usize;
        let mut actor = Actor::decode(&data, count).unwrap();
        actor
            .load_sheath(&std::fs::read(path.with_extension("sheath")).unwrap())
            .unwrap();
        actor
            .load_lighting(&std::fs::read(path.with_extension("actorlight")).unwrap())
            .unwrap();
        let data = std::fs::read(path.with_extension("lightingposes")).unwrap();
        assert_eq!(&data[..8], b"OJCLR001");
        let mut r = Reader { data: &data, at: 8 };
        let frames = r.u32().unwrap();
        assert_eq!(r.u32().unwrap() as usize, count);
        let mut maximum = 0f32;
        let mut fixed = 0;
        for _ in 0..frames {
            let time = r.float().unwrap();
            for (_, _, color) in actor.render_vertices(f64::from(time)) {
                let expected = [r.float().unwrap(), r.float().unwrap(), r.float().unwrap()];
                if expected[0] < 0. {
                    assert!(color.is_none());
                    fixed += 1;
                } else {
                    let color = color.unwrap();
                    for i in 0..3 {
                        maximum = maximum.max((color[i] - expected[i]).abs());
                    }
                }
            }
        }
        assert_eq!(r.at, data.len());
        assert!(fixed > 0);
        println!("Animated lighting maximum RGB difference: {maximum}");
        assert!(maximum < 2e-5);
    }

    #[test]
    fn generated_light_uses_world_camera_and_inverse_placement() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
        let mut data = lighting_fixture(1);
        // Remove named light; retain ambient and a red generated contribution.
        data[12 + 6 * 4..12 + 7 * 4].copy_from_slice(&0f32.to_le_bytes());
        data[12 + 12 * 4..12 + 13 * 4].copy_from_slice(&0.5f32.to_le_bytes());
        actor.load_lighting(&data).unwrap();
        let m = [
            [0., 1., 0., 0.],
            [-1., 0., 0., 0.],
            [0., 0., 1., 0.],
            [10., 20., 30., 1.],
        ];
        actor.placement = Some((0, m));
        let camera = [10., 30., 30.];
        let value = actor.render_vertices_for_camera(0., camera, GeneratedLight::Dynamic);
        let expected = 0.1 + 0.5 * 0.3f32.sin();
        assert!((value[0].2.unwrap()[0] - expected).abs() < 1e-6);
        let away = actor.render_vertices_for_camera(0., [10., 10., 30.], GeneratedLight::Dynamic);
        assert!((away[0].2.unwrap()[0] - 0.1).abs() < 1e-6);
        assert_eq!(value[0].1, away[0].1);
        let off = actor.render_vertices_for_camera(0., camera, GeneratedLight::Disabled);
        assert_eq!(off[0].2, Some([0.1, 0., 0.]));
        let frozen = actor.render_vertices_for_camera(0., camera, GeneratedLight::Frozen);
        assert_eq!(frozen, actor.render_vertices(0.));
        let fallback =
            actor.render_vertices_for_camera(0., [10., 20., 30.], GeneratedLight::Dynamic);
        assert_eq!(fallback, frozen);
        actor.load_lighting(&lighting_fixture(0)).unwrap();
        assert_eq!(
            actor.render_vertices_for_camera(0., camera, GeneratedLight::Dynamic)[0].2,
            None
        );
    }
    #[test]
    fn generated_direction_handles_quadrants_and_invalid_inputs() {
        for camera in [[1., 0., 0.], [-1., 0., 0.], [0., 1., 0.], [0., -1., 0.]] {
            let d = generated_direction([0.; 3], camera).unwrap();
            assert!((d[0] * camera[0] + d[1] * camera[1] - 0.3f32.sin()).abs() < 1e-6);
            assert!((d[2] - 0.3f32.cos()).abs() < 1e-6);
        }
        assert!(generated_direction([0.; 3], [0., 0., 1.]).is_none());
        assert!(generated_direction([f32::NAN, 0., 0.], [1.; 3]).is_none());
        assert!(generated_direction([0.; 3], [f32::INFINITY, 0., 0.]).is_none());
    }

    #[test]
    fn light_origins_follow_bones_without_moving_geometry() {
        let mut actor = Actor::decode(&fixture(), 1).unwrap();
        actor.vertices.push((
            0,
            vec![Influence {
                bone: 0,
                weight: 1.,
                point: [0.; 3],
            }],
        ));
        let mut light = lighting_fixture(1);
        light[8..12].copy_from_slice(&2u32.to_le_bytes());
        light[36..40].copy_from_slice(&0f32.to_le_bytes());
        light[60..64].copy_from_slice(&0.5f32.to_le_bytes());
        light.extend(1u32.to_le_bytes());
        for x in [1f32, 0., 0.] {
            light.extend(x.to_le_bytes());
        }
        actor.load_lighting(&light).unwrap();
        actor.placement = Some((
            0,
            [
                [1., 0., 0., 0.],
                [0., 1., 0., 0.],
                [0., 0., 1., 0.],
                [0., 0., 0., 1.],
            ],
        ));
        let mut bytes = b"OJAORG01".to_vec();
        for x in [2, u32::MAX, 1] {
            bytes.extend(x.to_le_bytes());
        }
        actor.load_light_origins(&bytes).unwrap();
        let first = actor.render_vertices_for_camera(0., [20., 10., 0.], GeneratedLight::Dynamic);
        assert_eq!(first[0].1, first[1].1);
        assert!(first[0].2.unwrap()[0] > first[1].2.unwrap()[0]);
        assert!((first[1].2.unwrap()[0] - (0.1 + 0.5 * 0.3f32.sin() / 2f32.sqrt())).abs() < 1e-6);
        let next = actor.render_vertices_for_camera(1., [20., 10., 0.], GeneratedLight::Dynamic);
        assert_eq!(first[0].2, next[0].2);
        assert!((next[1].2.unwrap()[0] - 0.1).abs() < 1e-6);
        for n in 0..bytes.len() {
            assert!(actor.load_light_origins(&bytes[..n]).is_err());
        }
        let mut bad = bytes.clone();
        bad[16..20].copy_from_slice(&2u32.to_le_bytes());
        assert!(actor.load_light_origins(&bad).is_err());
        bad = bytes.clone();
        bad.extend(0u32.to_le_bytes());
        assert!(actor.load_light_origins(&bad).is_err());
        bad = bytes.clone();
        bad[8..12].copy_from_slice(&1u32.to_le_bytes());
        assert!(actor.load_light_origins(&bad).is_err());
        assert_eq!(
            first,
            actor.render_vertices_for_camera(0., [20., 10., 0.], GeneratedLight::Dynamic)
        );
    }

    #[test]
    #[ignore = "Requires private menu package with source receiver origins"]
    fn source_receiver_origins_affect_only_mapped_colors() {
        let path = std::path::PathBuf::from(std::env::var("OPENJADE_ORIGIN_SCENE").unwrap());
        let mut scene = crate::Scene::load(&path).unwrap();
        let actor = scene.actor.as_mut().unwrap();
        let origins = actor.light_origins.take().unwrap();
        assert_eq!(origins.bones, vec![None, Some(3), Some(5)]);
        let camera = [-92.80204, -0.96494, 3.93218];
        let common = actor.render_vertices_for_camera(2., camera, GeneratedLight::Dynamic);
        actor.light_origins = Some(origins);
        let individual = actor.render_vertices_for_camera(2., camera, GeneratedLight::Dynamic);
        let slots = &actor.light_origins.as_ref().unwrap().slots;
        let mut changes = 0;
        let mut maximum = 0f32;
        for (i, (a, b)) in common.iter().zip(&individual).enumerate() {
            assert_eq!(a.0, b.0);
            assert_eq!(a.1, b.1);
            if slots[i] == 0 {
                assert_eq!(a.2, b.2);
            }
            if let (Some(x), Some(y)) = (a.2, b.2) {
                let error = (0..3).map(|j| (x[j] - y[j]).abs()).fold(0f32, f32::max);
                if error > 0. {
                    changes += 1;
                    maximum = maximum.max(error);
                }
            }
        }
        assert!(changes > 0);
        assert!(maximum < 0.01);
        println!("receiver origin changed_vertices={changes} maximum_rgb_delta={maximum}");
    }

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
                        *xyz.get(col).unwrap()
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
        let mut actor = Actor::decode(&data, count).unwrap();
        if let Ok(control) = std::fs::read(path.with_extension("sheath")) {
            actor.load_sheath(&control).unwrap();
        }
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
