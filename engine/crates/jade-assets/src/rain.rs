//! Independently implemented, bounded menu rain. Native data arrives in a local sidecar.
//! A private seed and 60 Hz scheduling provide repeatable research poses, not game RNG sync.
use crate::{invalid, Draw, Scene};
use std::io;
const H: f32 = f32::from_bits(0x3c88893b);
const K: f32 = f32::from_bits(0x3c088723);
const TICK: f64 = 1. / 60.;

#[derive(Clone)]
struct Config {
    matrix: [f32; 16],
    capacity: usize,
    values: [f32; 18],
    colors: [u32; 4],
    splash: Option<[f32; 3]>,
    bird_delay: Option<u8>,
    pollen: Option<[f32; 7]>,
    fog: bool,
}
#[derive(Clone, Debug)]
struct Particle {
    phase: u8,
    tile_step: u8,
    tile_clock: u8,
    rotation: u32,
    position: [f32; 3],
    velocity: [f32; 3],
    inverse: f32,
    remaining: f32,
    sizes: [f32; 2],
}
struct Emitter {
    config: Config,
    particles: Vec<Particle>,
    emission: f32,
    simulation: f32,
}
pub struct Rain {
    pub first: usize,
    pub vertices: Vec<f32>,
    pub alphas: Vec<u8>,
    emitters: Vec<Emitter>,
    seed: u32,
    pending: f64,
    layer: f32,
    pub billboard: [[f32; 3]; 2],
}
fn unit(seed: &mut u32) -> f32 {
    *seed = seed.wrapping_mul(214013).wrapping_add(2531011);
    ((*seed >> 16) & 32767) as f32 / 32767.
}
fn sample(seed: &mut u32, a: f32, b: f32) -> f32 {
    // The x87 range expression rounds only on its final float store.
    ((b as f64 - a as f64) * unit(seed) as f64 + a as f64) as f32
}
fn spawn(c: &Config, seed: &mut u32) -> Particle {
    let v = &c.values;
    if let Some([offset, spread_a, spread_b, angle_min, angle_max, spin_min, spin_max]) = c.pollen {
        let remaining = if c.fog {
            sample(seed, v[5], v[6])
        } else {
            sample(seed, v[7], v[8])
        };
        let sizes = [sample(seed, v[14], v[15]), sample(seed, v[16], v[17])];
        let x = sample(seed, -v[1], v[1]);
        let z = sample(seed, -v[2], v[2]);
        let a = sample(seed, -spread_a, spread_a);
        let b = sample(seed, -spread_a, spread_b);
        let speed = sample(seed, v[3], v[4]);
        use crate::palms::wave;
        let local = [
            speed * wave(a, 0) * wave(b, 256),
            -speed * wave(a, 256) * wave(b, 256),
            speed * wave(b, 0),
        ];
        let m = &c.matrix;
        let position =
            std::array::from_fn(|i| ((m[12 + i] + m[i] * x) + m[8 + i] * z) - offset * m[4 + i]);
        let velocity =
            std::array::from_fn(|i| local[0] * m[i] + local[1] * m[4 + i] + local[2] * m[8 + i]);
        let angle = (sample(seed, angle_min, angle_max) * f32::from_bits(0x4322f983)) as i32;
        let spin = (sample(seed, spin_min, spin_max) * 10430.378) as i32;
        let rotation = ((angle as u32) << 22)
            | (spin.unsigned_abs() & 0x7fff)
            | if spin < 0 { 0x8000 } else { 0 };
        return Particle {
            phase: if c.fog { 1 } else { 0 },
            tile_step: 0,
            tile_clock: 0,
            rotation,
            position,
            velocity,
            remaining,
            inverse: 1. / remaining,
            sizes,
        };
    }
    let mut remaining = sample(seed, v[5], v[6]);
    let mut phase = 1;
    if remaining == 0. {
        remaining = sample(seed, v[7], v[8]);
        phase = 0;
    }
    let width = sample(seed, v[14], v[15]);
    let height = if c.bird_delay.is_some() && c.capacity == 10 {
        width
    } else {
        sample(seed, v[16], v[17])
    };
    let sizes = [width, height];
    if let Some([offset, spread_a, spread_b]) = c.splash {
        use crate::palms::wave;
        let tau = std::f32::consts::TAU;
        let azimuth = sample(seed, 0., tau);
        let elevation = sample(seed, -tau / 4., tau / 4.);
        let radius = sample(seed, 0., v[1]);
        let a = sample(seed, -spread_a, spread_a);
        let b = sample(seed, -spread_a, spread_b);
        let speed = sample(seed, v[3], v[4]);
        let m = &c.matrix;
        let local = [
            radius * wave(azimuth, 256) * wave(elevation, 256),
            radius * wave(azimuth, 0) * wave(elevation, 256) - offset,
            radius * wave(elevation, 0),
        ];
        let direction = [
            speed * wave(a, 0) * wave(b, 256),
            -speed * wave(a, 256) * wave(b, 256),
            speed * wave(b, 0),
        ];
        let transform = |w: [f32; 3], i: usize| m[i] * w[0] + m[4 + i] * w[1] + m[8 + i] * w[2];
        return Particle {
            phase,
            tile_step: 0,
            tile_clock: 0,
            rotation: 0,
            position: std::array::from_fn(|i| m[12 + i] + transform(local, i)),
            velocity: std::array::from_fn(|i| transform(direction, i)),
            inverse: 1. / remaining,
            remaining,
            sizes,
        };
    }
    let x = ((2. * unit(seed) as f64 - 1.) * v[1] as f64) as f32;
    let z = ((2. * unit(seed) as f64 - 1.) * v[2] as f64) as f32;
    let speed = sample(seed, v[3], v[4]); // Zero speed still consumes a draw.
    let m = &c.matrix;
    let position = std::array::from_fn(|i| {
        ((m[12 + i] as f64 + m[i] as f64 * x as f64) as f32 as f64 + m[8 + i] as f64 * z as f64)
            as f32
    });
    Particle {
        phase,
        tile_step: 0,
        tile_clock: 0,
        rotation: 0,
        position,
        velocity: std::array::from_fn(|i| -speed * m[4 + i]),
        inverse: 1. / remaining,
        remaining,
        sizes,
    }
}
fn update(p: &mut Particle, c: &Config, elapsed: f32, steps: usize, seed: &mut u32) -> bool {
    while p.remaining < elapsed {
        let range = match p.phase {
            1 => {
                p.phase = 0;
                [7, 8]
            }
            0 => {
                p.phase = 2;
                [9, 10]
            }
            _ => return false,
        };
        p.remaining = sample(seed, c.values[range[0]], c.values[range[1]]);
        p.inverse = 1. / p.remaining;
    }
    p.remaining -= elapsed;
    if c.pollen.is_some() {
        // This packed angle advances once per emitter update, even with zero motion steps.
        let speed = p.rotation & 0x7fff;
        let increment = speed << 16;
        p.rotation = if p.rotation & 0x8000 == 0 {
            p.rotation.wrapping_add(increment)
        } else {
            p.rotation.wrapping_sub(increment)
        };
    }
    for _ in 0..steps {
        for i in 0..3 {
            let dv = c.values[11 + i] * H;
            p.position[i] = (p.position[i] + dv * K) + p.velocity[i] * H;
            p.velocity[i] += dv;
        }
    }
    true
}
fn packed_lerp(a: u32, b: u32, t: f32) -> u32 {
    if t >= 0.98 {
        return b;
    }
    if t <= 0.02 {
        return a;
    }
    let bits = (t + 49152.).to_bits();
    (1..8)
        .map(|s| {
            let value = if bits & (1 << (8 - s)) != 0 { b } else { a };
            let mask = ((1u32 << (8 - s)) - 1) * 0x01010101;
            (value >> s) & mask
        })
        .sum()
}
fn corners(
    p: &Particle,
    c: &Config,
    layer: f32,
    axes: Option<[[f32; 3]; 2]>,
) -> ([[f32; 9]; 6], u8) {
    let mut ratio = p.remaining * p.inverse;
    let mut sizes = p.sizes;
    let color = match p.phase {
        1 => {
            ratio = 1. - ratio;
            if !c.fog && c.splash.is_none() && c.bird_delay.is_none() {
                for s in &mut sizes {
                    *s *= ratio;
                }
            }
            packed_lerp(c.colors[0], c.colors[1], ratio)
        }
        2 => packed_lerp(c.colors[3], c.colors[2], ratio),
        _ => packed_lerp(c.colors[2], c.colors[1], ratio),
    };
    let mut alpha = (color >> 24) as u8;
    if c.splash.is_some() && p.phase != 0 && ratio < 0.98 {
        let bits = (ratio + 49152.).to_bits();
        alpha = if ratio <= 0.02 {
            0
        } else {
            (1..=5)
                .filter(|s| bits & (1 << (8 - s)) != 0)
                .map(|s| alpha >> s)
                .sum()
        };
    }
    let [u, v] = axes.unwrap_or_else(|| {
        [
            c.matrix[..3].try_into().unwrap(),
            c.matrix[4..7].try_into().unwrap(),
        ]
    });
    let signs = [[-1., -1.], [-1., 1.], [1., 1.], [1., -1.]];
    let uvs = [[0., 1.], [0., 0.], [1., 0.], [1., 1.]];
    let frame = if p.tile_step <= 7 {
        p.tile_step
    } else {
        14 - p.tile_step
    };
    let quad: [[f32; 9]; 4] = std::array::from_fn(|j| {
        let xyz: [f32; 3] = std::array::from_fn(|i| {
            let (mut width, mut height) = (sizes[0] * u[i], sizes[1] * v[i]);
            if p.rotation != 0 {
                let index = (p.rotation >> 22) as usize;
                let sine = crate::palms::sine_index(index);
                let cosine = crate::palms::sine_index((index + 256) % 1023);
                (width, height) = (
                    width * cosine + height * sine,
                    height * cosine - width * sine,
                );
            }
            (p.position[i] + signs[j][0] * width) + signs[j][1] * height
        });
        [
            xyz[0],
            xyz[1],
            xyz[2],
            if c.bird_delay.is_some() {
                (f32::from(frame % 4) + uvs[j][0]) / 4.
            } else {
                uvs[j][0]
            },
            if c.bird_delay.is_some() {
                (1. - f32::from(frame / 4) + uvs[j][1]) / 2.
            } else {
                uvs[j][1]
            },
            (color & 255) as f32 / 255.,
            ((color >> 8) & 255) as f32 / 255.,
            ((color >> 16) & 255) as f32 / 255.,
            layer,
        ]
    });
    (
        [quad[0], quad[1], quad[2], quad[2], quad[3], quad[0]],
        alpha,
    )
}
#[derive(Clone, Copy, PartialEq)]
pub(crate) enum Effect {
    Rain,
    Splash,
    Birds,
    Pollen,
    Fog,
}
impl Rain {
    pub fn attach(scene: &mut Scene, bytes: &[u8]) -> io::Result<()> {
        Self::attach_effect(scene, bytes, Effect::Rain)
    }
    pub(crate) fn attach_effect(scene: &mut Scene, bytes: &[u8], effect: Effect) -> io::Result<()> {
        let splash = effect == Effect::Splash;
        let birds = effect == Effect::Birds;
        let fog = effect == Effect::Fog;
        let pollen = effect == Effect::Pollen;
        let (side, emitters_count, record_size, magic) = match effect {
            Effect::Rain => (32usize, 2usize, 156usize, b"OJRAIN01"),
            Effect::Splash => (64, 8, 168, b"OJSPLH01"),
            Effect::Pollen => (64, 1, 184, b"OJPOLL01"),
            Effect::Fog => (64, 2, 184, b"OJFOGG01"),
            Effect::Birds => (32, 2, 160, b"OJBIRD01"),
        };
        let pixels_start = 8 + emitters_count * record_size;
        if bytes.len() != pixels_start + side * side * 4
            || &bytes[..8] != magic
            || scene.width < side as u32
            || scene.height < side as u32
            || (if splash {
                scene.splashes.is_some()
            } else if birds {
                scene.birds.is_some()
            } else if fog {
                scene.fog.is_some()
            } else if pollen {
                scene.pollen.is_some()
            } else {
                scene.rain.is_some()
            })
            || scene.layers >= 256
            || scene.ui_start != scene.layers
        {
            return Err(invalid("Invalid rain sidecar/scene extent"));
        }
        let mut emitters = Vec::new();
        for n in 0..emitters_count {
            let start = 8 + n * record_size;
            let word = |i| u32::from_le_bytes(bytes[start + i..start + i + 4].try_into().unwrap());
            let matrix = std::array::from_fn(|i| f32::from_bits(word(i * 4)));
            let capacity = word(64) as usize;
            let values: [f32; 18] = std::array::from_fn(|i| f32::from_bits(word(68 + i * 4)));
            let colors = std::array::from_fn(|i| word(140 + i * 4));
            let splash_controls =
                splash.then(|| std::array::from_fn(|i| f32::from_bits(word(156 + i * 4))));
            let controls =
                (pollen || fog).then(|| std::array::from_fn(|i| f32::from_bits(word(156 + i * 4))));
            if controls.is_some_and(|v: [f32; 7]| {
                v.iter().any(|x| !x.is_finite() || x.abs() > 1000.) || v[3] > v[4] || v[5] > v[6]
            }) || splash_controls
                .is_some_and(|v: [f32; 3]| v.iter().any(|x| !x.is_finite() || x.abs() > 10000.))
                || capacity
                    != (if birds {
                        [5, 10][n]
                    } else if splash || pollen || fog {
                        20
                    } else {
                        150
                    })
                || (birds && bytes[start + 156..start + 160] != [4, 2, [10, 2][n], 4])
                || matrix
                    .iter()
                    .chain(values.iter())
                    .any(|x| !x.is_finite() || x.abs() > 10000.)
                || values[0] <= 0.
                || values[0] > 1000.
                || (!splash && !birds && !pollen && !fog && (values[3] != 0. || values[4] != 0.))
                || values[3] < 0.
                || values[4] < values[3]
                || values[1] < 0.
                || values[2] < 0.
                || [5, 7, 9, 14, 16].iter().any(|&i| {
                    values[i] < 0.
                        || values[i + 1] < 0.
                        || (!(fog && i == 9) && values[i + 1] < values[i])
                })
                || values[8] <= 0.
            {
                return Err(invalid("Unsupported rain parameters"));
            }
            emitters.push(Emitter {
                config: Config {
                    matrix,
                    capacity,
                    values,
                    colors,
                    splash: splash_controls,
                    pollen: controls,
                    fog,
                    bird_delay: birds.then(|| bytes[start + 158]),
                },
                particles: Vec::new(),
                emission: 0.,
                simulation: 0.,
            });
        }
        let first = scene.vertices.len() / 9;
        let total_corners = emitters
            .iter()
            .map(|e| e.config.capacity * 6)
            .sum::<usize>();
        let mut rain = Self {
            first,
            vertices: vec![0.; total_corners * 9],
            alphas: vec![0; total_corners],
            emitters,
            seed: 1,
            pending: 0.,
            layer: scene.layers as f32,
            billboard: [
                scene.camera[3..6].try_into().unwrap(),
                std::array::from_fn(|i| -scene.camera[6 + i]),
            ],
        };
        rain.rebuild();
        scene.vertices.extend_from_slice(&rain.vertices);
        let base = scene.pixels.len();
        scene
            .pixels
            .resize(base + (scene.width * scene.height * 4) as usize, 0);
        for y in 0..side {
            let dst = base + y * scene.width as usize * 4;
            scene.pixels[dst..dst + side * 4].copy_from_slice(
                &bytes[pixels_start + y * side * 4..pixels_start + (y + 1) * side * 4],
            );
        }
        scene.texture_sizes.push([side as u32, side as u32]);
        scene.layers += 1;
        scene.ui_start = scene.layers;
        let mut cursor = first;
        for emitter in &rain.emitters {
            let count = emitter.config.capacity * 6;
            scene.draws.push(Draw {
                first: cursor as u32,
                count: count as u32,
                blend: if splash || birds || fog { 1 } else { 6 },
                vertex_fog: if splash || birds || fog { 5 } else { 4 },
                parameters: [1., 1., 0., 0., 1., 2., 0., 1.],
            });
            scene.uv_rates.push([0.; 2]);
            cursor += count;
        }
        if splash {
            scene.splashes = Some(rain)
        } else {
            if birds {
                scene.birds = Some(rain);
            } else if fog {
                scene.fog = Some(rain);
            } else if pollen {
                scene.pollen = Some(rain);
            } else {
                scene.rain = Some(rain);
            }
        }
        Ok(())
    }
    pub fn advance(&mut self, dt: f32) {
        if !dt.is_finite() || !(0. ..=120.).contains(&dt) {
            return;
        }
        self.pending += dt as f64;
        while self.pending >= TICK {
            self.pending -= TICK;
            self.tick(TICK as f32);
        }
        self.rebuild();
    }
    /// Pollen rotates once per displayed update. Fixed-time research captures use advance().
    pub fn advance_frame(&mut self, dt: f32) {
        if dt.is_finite() && dt > 0. && dt <= 0.1 {
            self.tick(dt);
        }
        self.rebuild();
    }
    fn tick(&mut self, dt: f32) {
        for e in &mut self.emitters {
            let combined = e.simulation + dt;
            let steps = (combined as f64 * 60.).max(0.) as usize;
            let elapsed = steps as f32 * H;
            e.simulation = combined - elapsed;
            let mut i = 0;
            while i < e.particles.len() {
                if let Some(delay) = e.config.bird_delay {
                    let p = &mut e.particles[i];
                    if p.tile_clock >= delay {
                        p.tile_clock = 0;
                        p.tile_step = (p.tile_step + 1) % 14;
                    } else {
                        p.tile_clock = (f32::from(p.tile_clock) + 120. * dt).trunc() as u8;
                    }
                }
                if update(
                    &mut e.particles[i],
                    &e.config,
                    elapsed,
                    steps,
                    &mut self.seed,
                ) {
                    i += 1;
                } else {
                    e.particles.swap_remove(i);
                }
            }
            let combined = e.emission + dt;
            let count = (combined as f64 * e.config.values[0] as f64).max(0.) as usize;
            e.emission = (combined as f64 - count as f64 / e.config.values[0] as f64) as f32;
            for _ in 0..count.min(e.config.capacity - e.particles.len()) {
                e.particles.push(spawn(&e.config, &mut self.seed));
            }
        }
    }
    fn rebuild(&mut self) {
        self.alphas.fill(0);
        let mut base = 0;
        for e in &self.emitters {
            for slot in 0..e.config.capacity {
                let start = base + slot * 6;
                if let Some(p) = e.particles.get(slot) {
                    let (verts, alpha) = corners(
                        p,
                        &e.config,
                        self.layer,
                        (e.config.splash.is_some()
                            || e.config.bird_delay.is_some()
                            || e.config.pollen.is_some())
                        .then_some(self.billboard),
                    );
                    for (j, v) in verts.iter().enumerate() {
                        self.vertices[(start + j) * 9..(start + j + 1) * 9].copy_from_slice(v);
                    }
                    self.alphas[start..start + 6].fill(alpha);
                } else {
                    for j in 0..6 {
                        let v = &mut self.vertices[(start + j) * 9..(start + j + 1) * 9];
                        v.fill(0.);
                        v[..3].copy_from_slice(&e.config.matrix[12..15]);
                        v[8] = self.layer;
                    }
                }
            }
            base += e.config.capacity * 6;
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        Config {
            splash: None,
            bird_delay: None,
            pollen: None,
            fog: false,
            matrix: [
                1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.,
            ],
            capacity: 150,
            values: [
                50., 4., 6., 0., 0., 0., 0.1, 1., 1., 0., 0.6, 0., 0., -70., 0.1, 0.8, 1., 2.,
            ],
            colors: [0x00010101, 0xdfebe5de, 0xdeede7e0, 0],
        }
    }
    #[test]
    fn pollen_starts_in_main_and_rotates_between_motion_steps() {
        let mut config = config();
        config.pollen = Some([0.1, 0.5, 0.8, 0., 0., 0., 0.004]);
        config.values[3..9].copy_from_slice(&[0.8, 1., 0., 0., 4., 12.]);
        let mut seed = 1u32;
        let mut particle = spawn(&config, &mut seed);
        assert_eq!(particle.phase, 0);
        assert!((4. ..=12.).contains(&particle.remaining));
        let speed = particle.velocity.iter().map(|v| v * v).sum::<f32>().sqrt();
        assert!((0.79..=1.01).contains(&speed));
        let before = particle.position;
        particle.rotation = 6;
        assert!(update(&mut particle, &config, 0., 0, &mut seed));
        assert_eq!(particle.position, before);
        assert_eq!(particle.rotation, 0x60006);
    }
    #[test]
    fn native_creation_samples() {
        for (seed, expected) in [
            (
                1,
                [
                    2.469923973,
                    1.020112038,
                    0.000125125895,
                    0.494509757,
                    1.193304300,
                ],
            ),
            (
                42,
                [
                    3.338114738,
                    -0.110049605,
                    0.000534073915,
                    0.108545184,
                    1.545335293,
                ],
            ),
            (
                12345,
                [
                    1.401776314,
                    -3.865657568,
                    0.023145238,
                    0.509399712,
                    1.787225008,
                ],
            ),
        ] {
            let p = spawn(&config(), &mut seed.clone());
            for (a, b) in [
                p.position[0],
                p.position[2],
                p.remaining,
                p.sizes[0],
                p.sizes[1],
            ]
            .into_iter()
            .zip(expected)
            {
                assert!((a as f64 - b).abs() < 2e-6);
            }
        }
    }
    #[test]
    fn native_motion_and_strict_expiry() {
        let c = config();
        let mut p = spawn(&c, &mut 1);
        p.position = [0.; 3];
        p.phase = 0;
        p.remaining = 1.;
        assert!(update(&mut p, &c, 6. * H, 6, &mut 1));
        assert_eq!(p.position[2], -0.35001048);
        assert_eq!(p.velocity[2], -7.0001397);
        p.phase = 2;
        p.remaining = H;
        assert!(update(&mut p, &c, H, 1, &mut 42));
        assert_eq!(p.remaining, 0.);
        assert!(!update(&mut p, &c, H, 1, &mut 42));
        p.phase = 1;
        p.remaining = 0.;
        assert!(update(&mut p, &c, H, 1, &mut 42));
        assert_eq!(p.phase, 0);
        p.phase = 0;
        p.remaining = 0.;
        assert!(!update(&mut p, &c, H, 1, &mut 42));
    }
    #[test]
    fn packed_colors_and_corner_order() {
        assert_eq!(packed_lerp(0, u32::MAX, 0.5), 0x7f7f7f7f);
        assert_eq!(packed_lerp(u32::MAX, u32::MAX, 0.5), 0xf7f7f7f7);
        let mut c = config();
        c.matrix[5] = 0.;
        c.matrix[6] = -1.;
        c.colors = [0, u32::MAX, u32::MAX, 0];
        let mut p = spawn(&c, &mut 1);
        p.position = [10., 20., 30.];
        p.sizes = [2., 4.];
        p.inverse = 1.;
        p.remaining = 0.5;
        let (v, a) = corners(&p, &c, 7., None);
        assert_eq!(&v[0][..5], &[9., 20., 32., 0., 1.]);
        assert_eq!(&v[2][..5], &[11., 20., 28., 1., 0.]);
        assert_eq!(a, 127);
    }
    fn fixture() -> (Scene, Vec<u8>) {
        let mut b = b"OJSCN001".to_vec();
        for v in [3u32, 32, 32, 1] {
            b.extend(v.to_le_bytes());
        }
        for v in [0f32, 0., 0., 1., 0., 0., 0., 1., 0., 0., 0., 1., 60.] {
            b.extend(v.to_le_bytes());
        }
        for _ in 0..3 {
            for v in [0f32, 0., 2., 0., 0., 1., 1., 1., 0.] {
                b.extend(v.to_le_bytes());
            }
        }
        b.extend([255u8; 4096]);
        let scene = Scene::decode(&b).unwrap();
        let mut side = b"OJRAIN01".to_vec();
        let c = config();
        for _ in 0..2 {
            for f in c.matrix {
                side.extend(f.to_le_bytes());
            }
            side.extend((c.capacity as u32).to_le_bytes());
            for f in c.values {
                side.extend(f.to_le_bytes());
            }
            for v in c.colors {
                side.extend(v.to_le_bytes());
            }
        }
        side.extend([127u8; 4096]);
        (scene, side)
    }
    #[test]
    fn bounded_sidecar_and_transactional_rejection() {
        let (mut scene, b) = fixture();
        for bytes in [&b[..b.len() - 1], &[b.clone(), vec![0]].concat()] {
            assert!(Rain::attach(&mut scene, bytes).is_err());
            assert_eq!(scene.layers, 1);
            assert_eq!(scene.vertices.len(), 27);
        }
        let mut bad = b.clone();
        bad[76..80].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(Rain::attach(&mut scene, &bad).is_err());
        Rain::attach(&mut scene, &b).unwrap();
        assert_eq!(scene.layers, 2);
        assert_eq!(scene.ui_start, 2);
        assert_eq!(scene.texture_pixels(1), vec![127; 4096]);
        assert_eq!(scene.vertices.len(), 27 + 1800 * 9);
        assert_eq!(scene.draws[1].blend, 6);
        assert!(Rain::attach(&mut scene, &b).is_err());
    }
    #[test]
    fn deterministic_clock_and_population_bounds() {
        let (mut a, b) = fixture();
        let (mut other, _) = fixture();
        Rain::attach(&mut a, &b).unwrap();
        Rain::attach(&mut other, &b).unwrap();
        let a = a.rain.as_mut().unwrap();
        let other = other.rain.as_mut().unwrap();
        a.advance(2.);
        for _ in 0..8 {
            other.advance(0.25);
        }
        assert_eq!(a.vertices, other.vertices);
        assert_eq!(a.alphas, other.alphas);
        assert!(a.alphas.iter().any(|&x| x > 0));
        for _ in 0..300 {
            a.advance(0.1);
            assert!(a
                .emitters
                .iter()
                .all(|e| !e.particles.is_empty() && e.particles.len() <= 150));
            assert!(a.vertices.iter().all(|x| x.is_finite()));
        }
    }
    #[test]
    fn extended_emission_product_and_phase_colors() {
        let (mut a, b) = fixture();
        Rain::attach(&mut a, &b).unwrap();
        let a = a.rain.as_mut().unwrap();
        a.tick(0.02);
        assert!(a.emitters.iter().all(|e| e.particles.is_empty()));
        a.tick(0.01);
        assert!(a.emitters.iter().all(|e| e.particles.len() == 1));
        let c = config();
        let mut p = spawn(&c, &mut 1);
        p.inverse = 1.;
        for (phase, remaining, color) in [
            (1, 1., c.colors[0]),
            (0, 1., c.colors[1]),
            (0, 0., c.colors[2]),
            (2, 0., c.colors[3]),
        ] {
            p.phase = phase;
            p.remaining = remaining;
            let (v, alpha) = corners(&p, &c, 1., None);
            assert_eq!(alpha, (color >> 24) as u8);
            assert_eq!(v[0][5], (color & 255) as f32 / 255.);
        }
    }
    #[test]
    #[ignore = "Requires local original-game captures; set OPENJADE_RAIN_CAPTURES"]
    fn native_captured_vertices() {
        let directory =
            std::env::var("OPENJADE_RAIN_CAPTURES").expect("Capture directory required");
        check_draws(directory, None, Effect::Rain);
    }
    #[test]
    #[ignore = "Requires OPENJADE_SPLASH_CAPTURES and OPENJADE_SPLASH_SCENE"]
    fn native_splash_corners() {
        let path = std::env::var("OPENJADE_SPLASH_SCENE").unwrap();
        let scene = Scene::load(std::path::Path::new(&path)).unwrap();
        check_draws(
            std::env::var("OPENJADE_SPLASH_CAPTURES").unwrap(),
            Some(scene.splashes.unwrap().billboard),
            Effect::Splash,
        );
    }
    #[test]
    #[ignore = "Requires local GOG bird captures and a prepared scene"]
    fn native_bird_corners() {
        let path = std::env::var("OPENJADE_BIRD_SCENE").unwrap();
        let scene = Scene::load(std::path::Path::new(&path)).unwrap();
        check_draws(
            std::env::var("OPENJADE_BIRD_CAPTURES").unwrap(),
            Some(scene.birds.unwrap().billboard),
            Effect::Birds,
        );
    }
    fn check_draws(directory: String, axes: Option<[[f32; 3]; 2]>, effect: Effect) {
        let birds = effect == Effect::Birds;
        let fog = effect == Effect::Fog;
        let pollen = effect == Effect::Pollen;
        let mut max_error = 0_f32;
        let mut counts = [0usize; 3];
        let mut draws = 0;
        for entry in std::fs::read_dir(directory).unwrap() {
            let path = entry.unwrap().path();
            if path.extension().is_none_or(|x| x != "vb")
                || !path
                    .file_name()
                    .unwrap()
                    .to_string_lossy()
                    .starts_with(if fog {
                        "fog-life-"
                    } else if pollen {
                        "pollen-native-"
                    } else if birds {
                        "birds-track-"
                    } else if axes.is_some() {
                        "splash-draw-"
                    } else {
                        "rain-v-"
                    })
            {
                continue;
            }
            let raw = std::fs::read(&path).unwrap();
            let particles = std::fs::read(path.with_extension("particles")).unwrap();
            let d = std::fs::read(path.with_extension("descriptor")).unwrap();
            assert_eq!(d.len(), 0x164);
            assert_eq!(particles.len() % 48, 0);
            assert_eq!(raw.len(), particles.len() / 48 * 216);
            let word = |b: &[u8], i: usize| u32::from_le_bytes(b[i..i + 4].try_into().unwrap());
            if birds {
                assert!(matches!(word(&d, 0x14), 0x80000047 | 0x8000004a));
            } else {
                assert_eq!(
                    word(&d, 0x14),
                    if pollen || fog {
                        0x80001041
                    } else if axes.is_some() {
                        0x20149
                    } else {
                        0x08020241
                    }
                );
            }
            assert_eq!(&d[0xf5..0xf7], &[0, 0]);
            let mut c = config();
            c.matrix = [
                1., 0., 0., 0., 0., 0., -1., 0., 0., 1., 0., 0., 0., 0., 0., 1.,
            ];
            c.fog = fog;
            if pollen || fog {
                c.pollen = Some([0.; 7]);
            } else if birds {
                c.bird_delay = Some(d[0xf2]);
            } else {
                c.splash = axes.map(|_| [0.2, 0.9, 0.8]);
            }
            c.colors = [0xe8, 0xe0, 0xe4, 0xec].map(|i| word(&d, i));
            for (j, b) in particles.as_chunks::<48>().0.iter().enumerate() {
                let flags = word(b, 0);
                let phase = (flags & 3) as u8;
                counts[phase as usize] += 1;
                let v: [f32; 11] = std::array::from_fn(|i| f32::from_bits(word(b, 4 + i * 4)));
                let p = Particle {
                    phase,
                    tile_step: if birds { ((flags >> 8) & 127) as u8 } else { 0 },
                    tile_clock: 0,
                    rotation: word(b, 28),
                    position: v[..3].try_into().unwrap(),
                    velocity: v[3..6].try_into().unwrap(),
                    inverse: v[7],
                    remaining: v[8],
                    sizes: v[9..].try_into().unwrap(),
                };
                let (vertices, alpha) = corners(&p, &c, 0., axes);
                for (k, v) in vertices.iter().enumerate() {
                    let start = (j * 6 + k) * 36;
                    for (i, value) in v.iter().take(3).enumerate() {
                        let target = word(&raw, start + i * 4);
                        if axes.is_none() {
                            assert_eq!(value.to_bits(), target);
                        }
                        max_error = max_error.max((value - f32::from_bits(target)).abs());
                    }
                    for i in 0..2 {
                        assert_eq!(v[3 + i].to_bits(), word(&raw, start + 28 + i * 4));
                    }
                    let argb = word(&raw, start + 24);
                    assert_eq!(alpha, (argb >> 24) as u8);
                    for (i, shift) in [16, 8, 0].into_iter().enumerate() {
                        assert_eq!(v[5 + i], ((argb >> shift) & 255) as f32 / 255.);
                    }
                }
            }
            draws += 1;
        }
        if pollen {
            assert!(counts[0] > 0 && counts[1] == 0 && counts[2] > 0 && max_error < 0.00002);
        } else if birds {
            assert!(counts[1] > 0);
        } else {
            assert!(counts.iter().all(|&n| n > 0));
        }
        assert!(max_error < 0.002, "{max_error}");
        println!(
            "Native capture, max XYZ error {max_error}: {draws} draws, {counts:?} particles by phase; {} corners checked",
            counts.iter().sum::<usize>() * 6
        );
    }
    #[test]
    #[ignore = "Requires local pollen GOG draw captures and a prepared scene"]
    fn native_pollen_draws() {
        let scene = Scene::load(std::path::Path::new(
            &std::env::var("OPENJADE_POLLEN_SCENE").unwrap(),
        ))
        .unwrap();
        check_draws(
            std::env::var("OPENJADE_POLLEN_CAPTURES").unwrap(),
            Some(scene.pollen.unwrap().billboard),
            Effect::Pollen,
        );
    }
    #[test]
    #[ignore = "Requires local pollen GOG emission captures and a prepared scene"]
    fn native_pollen_birth_and_motion() {
        use std::collections::HashMap;
        let scene = Scene::load(std::path::Path::new(
            &std::env::var("OPENJADE_POLLEN_SCENE").unwrap(),
        ))
        .unwrap();
        let pollen = scene.pollen.unwrap();
        let config = &pollen.emitters[0].config;
        let dir = std::path::PathBuf::from(std::env::var("OPENJADE_POLLEN_CAPTURES").unwrap());
        let word = |b: &[u8], o: usize| u32::from_le_bytes(b[o..o + 4].try_into().unwrap());
        let val = |b: &[u8], o: usize| f32::from_bits(word(b, o));
        let mut random: HashMap<u32, Vec<u32>> = HashMap::new();
        let rng = std::fs::read(dir.join("pollen-native-rng.bin")).unwrap();
        assert_eq!(rng.len() % 8, 0);
        for row in rng.as_chunks::<8>().0 {
            random.entry(word(row, 0)).or_default().push(word(row, 4));
        }
        let states = std::fs::read(dir.join("pollen-native-states.bin")).unwrap();
        let mut tail = states.as_slice();
        let mut last: HashMap<[u32; 3], Particle> = HashMap::new();
        let (mut births, mut updates, mut changes) = (0, 0, 0);
        let (mut pos_error, mut vel_error, mut remainder) = (0_f32, 0_f32, 0_f32);
        while !tail.is_empty() {
            let (head, rest) = tail.split_at(20);
            let frame = word(head, 0);
            let dt = val(head, 4);
            let old = word(head, 8) as usize;
            let new = word(head, 12) as usize;
            assert!(old <= new && new <= 20);
            let (slots, rest) = rest.split_at(new * 48);
            tail = rest;
            let steps = ((remainder + dt) as f64 * 60.) as usize;
            let elapsed = steps as f32 * H;
            remainder = val(head, 16);
            let mut next = HashMap::new();
            for (slot, b) in slots.as_chunks::<48>().0.iter().enumerate() {
                let velocity = std::array::from_fn(|i| word(b, 16 + 4 * i));
                let actual = Particle {
                    phase: (word(b, 0) & 3) as u8,
                    tile_clock: 0,
                    tile_step: 0,
                    rotation: word(b, 28),
                    position: std::array::from_fn(|i| val(b, 4 + i * 4)),
                    velocity: velocity.map(f32::from_bits),
                    inverse: val(b, 32),
                    remaining: val(b, 36),
                    sizes: [val(b, 40), val(b, 44)],
                };
                if slot >= old {
                    let values = &random[&frame][(slot - old) * 10..(slot - old + 1) * 10];
                    // The top state bit does not affect the 15-bit CRT outputs.
                    let mut seed = (0..65536u32)
                        .map(|lo| {
                            ((values[0] << 16) | lo)
                                .wrapping_sub(2531011)
                                .wrapping_mul(0xb9b33155)
                        })
                        .find(|&s| {
                            let mut state = s;
                            values.iter().all(|&v| {
                                state = state.wrapping_mul(214013).wrapping_add(2531011);
                                (state >> 16) & 32767 == v
                            })
                        })
                        .unwrap();
                    let predicted = spawn(config, &mut seed);
                    assert_eq!(predicted.phase, actual.phase);
                    assert_eq!(predicted.rotation, actual.rotation);
                    assert!((predicted.remaining - actual.remaining).abs() < 0.000002);
                    for i in 0..2 {
                        assert!((predicted.sizes[i] - actual.sizes[i]).abs() < 0.000001);
                    }
                    for i in 0..3 {
                        pos_error =
                            pos_error.max((predicted.position[i] - actual.position[i]).abs());
                        vel_error =
                            vel_error.max((predicted.velocity[i] - actual.velocity[i]).abs());
                    }
                    births += 1;
                } else {
                    let mut previous = last.get(&velocity).unwrap().clone();
                    if actual.phase == previous.phase {
                        assert!(update(&mut previous, config, elapsed, steps, &mut 1));
                        assert_eq!(previous.rotation, actual.rotation);
                        assert!((previous.remaining - actual.remaining).abs() < 0.000002);
                        for i in 0..3 {
                            pos_error =
                                pos_error.max((previous.position[i] - actual.position[i]).abs());
                        }
                        updates += 1;
                    } else {
                        assert_eq!((previous.phase, actual.phase), (0, 2));
                        changes += 1;
                    }
                }
                assert!(next.insert(velocity, actual).is_none());
            }
            last = next;
        }
        assert!(
            births >= 20
                && updates > 1000
                && changes > 0
                && pos_error < 0.00002
                && vel_error < 0.000001
        );
        println!("{births} births, {updates} motion updates, {changes} observed main/end transitions; max position error {pos_error}, velocity {vel_error}");
    }
    #[test]
    #[ignore = "Requires local fog-life captures and prepared scene"]
    fn native_fog_draws() {
        let scene = Scene::load(std::path::Path::new(
            &std::env::var("OPENJADE_FOG_SCENE").unwrap(),
        ))
        .unwrap();
        check_draws(
            std::env::var("OPENJADE_FOG_CAPTURES").unwrap(),
            Some(scene.fog.unwrap().billboard),
            Effect::Fog,
        );
    }
    #[test]
    fn fog_starts_in_initial_and_keeps_size() {
        let mut c = config();
        c.fog = true;
        c.pollen = Some([0.; 7]);
        c.values[5] = 2.;
        c.values[6] = 3.;
        let mut p = spawn(&c, &mut 1);
        assert_eq!(p.phase, 1);
        p.rotation = 0;
        let a = corners(&p, &c, 0., None).0;
        p.remaining *= 0.5;
        let b = corners(&p, &c, 0., None).0;
        for (x, y) in a.iter().zip(b) {
            assert_eq!(x[..5], y[..5]);
        }
    }
}
