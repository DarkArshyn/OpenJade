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
}
#[derive(Clone, Debug)]
struct Particle {
    phase: u8,
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
    let mut remaining = sample(seed, v[5], v[6]);
    let mut phase = 1;
    if remaining == 0. {
        remaining = sample(seed, v[7], v[8]);
        phase = 0;
    }
    let sizes = [sample(seed, v[14], v[15]), sample(seed, v[16], v[17])];
    let x = ((2. * unit(seed) as f64 - 1.) * v[1] as f64) as f32;
    let z = ((2. * unit(seed) as f64 - 1.) * v[2] as f64) as f32;
    let _speed = sample(seed, v[3], v[4]); // Zero speed still consumes a draw.
    let m = &c.matrix;
    let position = std::array::from_fn(|i| {
        ((m[12 + i] as f64 + m[i] as f64 * x as f64) as f32 as f64 + m[8 + i] as f64 * z as f64)
            as f32
    });
    Particle {
        phase,
        position,
        velocity: [0.; 3],
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
fn corners(p: &Particle, c: &Config, layer: f32) -> ([[f32; 9]; 6], u8) {
    let mut ratio = p.remaining * p.inverse;
    let mut sizes = p.sizes;
    let color = match p.phase {
        1 => {
            ratio = 1. - ratio;
            for s in &mut sizes {
                *s *= ratio;
            }
            packed_lerp(c.colors[0], c.colors[1], ratio)
        }
        2 => packed_lerp(c.colors[3], c.colors[2], ratio),
        _ => packed_lerp(c.colors[2], c.colors[1], ratio),
    };
    let signs = [[-1., -1.], [-1., 1.], [1., 1.], [1., -1.]];
    let uvs = [[0., 1.], [0., 0.], [1., 0.], [1., 1.]];
    let quad: [[f32; 9]; 4] = std::array::from_fn(|j| {
        let xyz: [f32; 3] = std::array::from_fn(|i| {
            (p.position[i] + signs[j][0] * (sizes[0] * c.matrix[i]))
                + signs[j][1] * (sizes[1] * c.matrix[4 + i])
        });
        [
            xyz[0],
            xyz[1],
            xyz[2],
            uvs[j][0],
            uvs[j][1],
            (color & 255) as f32 / 255.,
            ((color >> 8) & 255) as f32 / 255.,
            ((color >> 16) & 255) as f32 / 255.,
            layer,
        ]
    });
    (
        [quad[0], quad[1], quad[2], quad[2], quad[3], quad[0]],
        (color >> 24) as u8,
    )
}
impl Rain {
    pub fn attach(scene: &mut Scene, bytes: &[u8]) -> io::Result<()> {
        if bytes.len() != 4416
            || &bytes[..8] != b"OJRAIN01"
            || scene.width < 32
            || scene.height < 32
            || scene.rain.is_some()
            || scene.layers >= 256
            || scene.ui_start != scene.layers
        {
            return Err(invalid("Invalid rain sidecar/scene extent"));
        }
        let mut emitters = Vec::new();
        for n in 0..2 {
            let start = 8 + n * 156;
            let word = |i| u32::from_le_bytes(bytes[start + i..start + i + 4].try_into().unwrap());
            let matrix = std::array::from_fn(|i| f32::from_bits(word(i * 4)));
            let capacity = word(64) as usize;
            let values: [f32; 18] = std::array::from_fn(|i| f32::from_bits(word(68 + i * 4)));
            let colors = std::array::from_fn(|i| word(140 + i * 4));
            if capacity != 150
                || matrix
                    .iter()
                    .chain(values.iter())
                    .any(|x| !x.is_finite() || x.abs() > 10000.)
                || values[0] <= 0.
                || values[0] > 1000.
                || values[3] != 0.
                || values[4] != 0.
                || values[1] < 0.
                || values[2] < 0.
                || [5, 7, 9, 14, 16]
                    .iter()
                    .any(|&i| values[i] < 0. || values[i + 1] < values[i])
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
                },
                particles: Vec::new(),
                emission: 0.,
                simulation: 0.,
            });
        }
        let first = scene.vertices.len() / 9;
        let mut rain = Self {
            first,
            vertices: vec![0.; 1800 * 9],
            alphas: vec![0; 1800],
            emitters,
            seed: 1,
            pending: 0.,
            layer: scene.layers as f32,
        };
        rain.rebuild();
        scene.vertices.extend_from_slice(&rain.vertices);
        let base = scene.pixels.len();
        scene
            .pixels
            .resize(base + (scene.width * scene.height * 4) as usize, 0);
        for y in 0..32 {
            let dst = base + y * scene.width as usize * 4;
            scene.pixels[dst..dst + 128]
                .copy_from_slice(&bytes[320 + y * 128..320 + (y + 1) * 128]);
        }
        scene.texture_sizes.push([32, 32]);
        scene.layers += 1;
        scene.ui_start = scene.layers;
        for n in 0..2 {
            scene.draws.push(Draw {
                first: (first + n * 900) as u32,
                count: 900,
                blend: 6,
                vertex_fog: 4,
                parameters: [1., 1., 0., 0., 1., 2., 0., 1.],
            });
            scene.uv_rates.push([0.; 2]);
        }
        scene.rain = Some(rain);
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
    fn tick(&mut self, dt: f32) {
        for e in &mut self.emitters {
            let combined = e.simulation + dt;
            let steps = (combined as f64 * 60.).max(0.) as usize;
            let elapsed = steps as f32 * H;
            e.simulation = combined - elapsed;
            let mut i = 0;
            while i < e.particles.len() {
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
        for (n, e) in self.emitters.iter().enumerate() {
            for slot in 0..e.config.capacity {
                let start = n * 900 + slot * 6;
                if let Some(p) = e.particles.get(slot) {
                    let (verts, alpha) = corners(p, &e.config, self.layer);
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
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn config() -> Config {
        Config {
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
        let (v, a) = corners(&p, &c, 7.);
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
            let (v, alpha) = corners(&p, &c, 1.);
            assert_eq!(alpha, (color >> 24) as u8);
            assert_eq!(v[0][5], (color & 255) as f32 / 255.);
        }
    }
    #[test]
    #[ignore = "Requires local original-game captures; set OPENJADE_RAIN_CAPTURES"]
    fn native_captured_vertices() {
        let directory =
            std::env::var("OPENJADE_RAIN_CAPTURES").expect("Capture directory required");
        let mut counts = [0usize; 3];
        let mut draws = 0;
        for entry in std::fs::read_dir(directory).unwrap() {
            let path = entry.unwrap().path();
            if path.extension().is_none_or(|x| x != "vb")
                || !path
                    .file_name()
                    .unwrap()
                    .to_string_lossy()
                    .starts_with("rain-v-")
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
            assert_eq!(word(&d, 0x14), 0x08020241);
            assert_eq!(&d[0xf5..0xf7], &[0, 0]);
            let mut c = config();
            c.matrix = [
                1., 0., 0., 0., 0., 0., -1., 0., 0., 1., 0., 0., 0., 0., 0., 1.,
            ];
            c.colors = [0xe8, 0xe0, 0xe4, 0xec].map(|i| word(&d, i));
            for (j, b) in particles.as_chunks::<48>().0.iter().enumerate() {
                let phase = word(b, 0) as u8;
                counts[phase as usize] += 1;
                let v: [f32; 11] = std::array::from_fn(|i| f32::from_bits(word(b, 4 + i * 4)));
                let p = Particle {
                    phase,
                    position: v[..3].try_into().unwrap(),
                    velocity: v[3..6].try_into().unwrap(),
                    inverse: v[7],
                    remaining: v[8],
                    sizes: v[9..].try_into().unwrap(),
                };
                let (vertices, alpha) = corners(&p, &c, 0.);
                for (k, v) in vertices.iter().enumerate() {
                    let start = (j * 6 + k) * 36;
                    for (i, value) in v.iter().take(3).enumerate() {
                        assert_eq!(value.to_bits(), word(&raw, start + i * 4));
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
        assert!(counts.iter().all(|&n| n > 0));
        println!(
            "Native rain: {draws} draws, {counts:?} particles by phase; {} corners matched exactly",
            counts.iter().sum::<usize>() * 6
        );
    }
}
