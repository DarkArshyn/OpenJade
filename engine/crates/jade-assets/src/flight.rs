//! Three native mesh birds. Waypoint steering and local wing deformation share no clock state.
use crate::{invalid, palms::wave, Draw, Scene};
use std::io;
type V = [f32; 3];
fn difference(a: V, b: V) -> V {
    std::array::from_fn(|i| a[i] - b[i])
}
fn dot(a: V, b: V) -> f32 {
    a.iter().zip(b).map(|(x, y)| x * y).sum()
}
fn direction(v: V) -> V {
    let len = dot(v, v).sqrt();
    if len > 1e-8 {
        v.map(|x| x / len)
    } else {
        [0.; 3]
    }
}
fn cross(a: V, b: V) -> V {
    [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]
}
#[derive(Clone, Copy)]
struct Node {
    center: V,
    low: V,
    high: V,
}
impl Node {
    fn contains(self, point: V) -> bool {
        let offset = difference(point, self.center);
        (0..3).all(|i| offset[i] >= self.low[i] && offset[i] <= self.high[i])
    }
}
struct Bird {
    nodes: [Node; 3],
    target: usize,
    position: V,
    heading: V,
    speed: f32,
    turn: f32,
    scale: f32,
    phase: f32,
    amplitude: f32,
    spatial: f32,
    rate: f32,
}
impl Bird {
    fn step(&mut self, dt: f32) {
        if self.nodes[self.target].contains(self.position) {
            self.target = (self.target + 1) % 3;
        }
        let goal = direction(difference(self.nodes[self.target].center, self.position));
        let previous = self.heading;
        for (v, h) in self.position.iter_mut().zip(previous) {
            *v += h * self.speed * dt;
        }
        let cosine = dot(previous, goal).clamp(-1., 1.);
        let tangent = direction(std::array::from_fn(|i| goal[i] - cosine * previous[i]));
        let angle = cosine.acos() * (self.turn * dt).min(1.);
        if cosine > 0.9999999 {
            self.heading = goal;
        } else if dot(tangent, tangent) > 0. {
            let (s, c) = angle.sin_cos();
            self.heading = direction(std::array::from_fn(|i| previous[i] * c + tangent[i] * s));
        }
        self.phase = (self.phase + self.rate * 30. * dt).rem_euclid(std::f32::consts::TAU);
    }
    fn basis(&self) -> [V; 3] {
        let x = direction(cross([0., 0., 1.], self.heading));
        let y = self.heading.map(|x| -x);
        [x, y, cross(x, y)]
    }
    fn wing_z(&self, corner: &[f32; 6]) -> f32 {
        let gain = corner[5] * self.amplitude;
        let x = wave(corner[0] * self.spatial + self.phase, 0);
        let y = wave(corner[1] * self.spatial + self.phase, 0);
        (corner[2] + x * gain) + y * gain
    }
}
pub struct Flight {
    pub first: usize,
    pub positions: Vec<V>,
    mesh: Vec<[f32; 6]>,
    birds: Vec<Bird>,
}
impl Flight {
    fn pose(&mut self) {
        for (bird, points) in self
            .birds
            .iter()
            .zip(self.positions.as_chunks_mut::<66>().0.iter_mut())
        {
            let axes = bird.basis();
            for (dst, corner) in points.iter_mut().zip(&self.mesh) {
                let z = bird.wing_z(corner);
                *dst = std::array::from_fn(|i| {
                    bird.position[i]
                        + bird.scale
                            * (corner[0] * axes[0][i] + corner[1] * axes[1][i] + z * axes[2][i])
                });
            }
        }
    }
    pub fn advance(&mut self, dt: f32) {
        if !dt.is_finite() || !(0. ..=120.).contains(&dt) {
            return;
        }
        // A fixed-time capture can request a complete flight interval in one call.
        let steps = if dt > 0.1 {
            (dt * 60.).ceil() as usize
        } else {
            1
        };
        for _ in 0..steps {
            for bird in &mut self.birds {
                bird.step(dt / steps as f32);
            }
        }
        self.pose();
    }
    pub fn attach(scene: &mut Scene, bytes: &[u8]) -> io::Result<()> {
        if bytes.len() != 6100
            || &bytes[..8] != b"OJFLT001"
            || scene.flight.is_some()
            || scene.width < 32
            || scene.height < 32
            || scene.layers >= 256
            || scene.ui_start != scene.layers
        {
            return Err(invalid("Invalid mesh flight sidecar"));
        }
        let mut floats = bytes[4108..]
            .as_chunks::<4>()
            .0
            .iter()
            .map(|b| f32::from_le_bytes(*b));
        let mesh: Vec<[f32; 6]> = (0..66)
            .map(|_| std::array::from_fn(|_| floats.next().unwrap()))
            .collect();
        if mesh
            .iter()
            .flatten()
            .any(|x| !x.is_finite() || x.abs() > 100.)
            || mesh.iter().any(|v| !(0. ..=1.).contains(&v[5]))
        {
            return Err(invalid("Invalid wing mesh"));
        }
        let mut birds = Vec::new();
        for _ in 0..3 {
            let params: [f32; 7] = std::array::from_fn(|_| floats.next().unwrap());
            let [speed, turn, scale, phase, amplitude, spatial, rate] = params;
            let mut vector = || std::array::from_fn(|_| floats.next().unwrap());
            let nodes: [Node; 3] = std::array::from_fn(|_| Node {
                center: vector(),
                low: vector(),
                high: vector(),
            });
            if params.iter().any(|x| !x.is_finite() || x.abs() > 100.)
                || speed <= 0.
                || turn <= 0.
                || scale <= 0.
                || nodes.iter().any(|n| {
                    (0..3).any(|i| {
                        !n.center[i].is_finite()
                            || n.center[i].abs() > 10000.
                            || !n.low[i].is_finite()
                            || !n.high[i].is_finite()
                            || n.low[i] >= n.high[i]
                    })
                })
                || (0..3).any(|i| {
                    let d = difference(nodes[i].center, nodes[(i + 1) % 3].center);
                    dot(d, d) < 1e-6
                })
            {
                return Err(invalid("Invalid bird path"));
            }
            birds.push(Bird {
                position: nodes[0].center,
                heading: direction(difference(nodes[1].center, nodes[0].center)),
                target: 1,
                nodes,
                speed,
                turn,
                scale,
                phase,
                amplitude,
                spatial,
                rate,
            });
        }
        let mut flight = Self {
            first: scene.vertices.len() / 9,
            positions: vec![[0.; 3]; 198],
            mesh,
            birds,
        };
        flight.pose();
        let rgb: [f32; 3] = std::array::from_fn(|i| bytes[8 + i] as f32 / 255.);
        for n in 0..3 {
            for (i, v) in flight.mesh.iter().enumerate() {
                let p = flight.positions[n * 66 + i];
                scene.vertices.extend([
                    p[0],
                    p[1],
                    p[2],
                    v[3],
                    v[4],
                    rgb[0],
                    rgb[1],
                    rgb[2],
                    scene.layers as f32,
                ]);
            }
            scene.draws.push(Draw {
                first: (flight.first + n * 66) as u32,
                count: 66,
                blend: 0,
                vertex_fog: 1,
                parameters: [1., 1., 0., 0., 1., 2., 0., 1.],
            });
            scene.uv_rates.push([0.; 2]);
        }
        let base = scene.pixels.len();
        scene
            .pixels
            .resize(base + (scene.width * scene.height * 4) as usize, 0);
        for y in 0..32 {
            let start = base + y * scene.width as usize * 4;
            scene.pixels[start..start + 128]
                .copy_from_slice(&bytes[12 + y * 128..12 + (y + 1) * 128]);
        }
        scene.texture_sizes.push([32, 32]);
        scene.layers += 1;
        scene.ui_start = scene.layers;
        scene.flight = Some(flight);
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Bird {
        let nodes = [[0., 0., 0.], [0., 2., 0.], [2., 2., 1.]].map(|center| Node {
            center,
            low: [-0.25; 3],
            high: [0.25; 3],
        });
        Bird {
            nodes,
            target: 1,
            position: [0., 1.8, 0.],
            heading: [0., 1., 0.],
            speed: 3.,
            turn: 1.,
            scale: 1.,
            phase: 0.,
            amplitude: 0.5,
            spatial: -0.15,
            rate: 0.07,
        }
    }
    #[test]
    fn enters_box_and_advances_on_previous_heading() {
        let mut bird = fixture();
        bird.step(0.1);
        assert_eq!(bird.target, 2);
        assert!(difference(bird.position, [0., 2.1, 0.])
            .iter()
            .all(|v| v.abs() < 1e-6));
        assert!(bird.heading[0] > 0. && bird.heading[2] > 0. && bird.heading[1] > 0.9);
        bird.position = [1.8, 1.8, 1.2];
        bird.step(0.1);
        assert_eq!(bird.target, 0);
    }
    #[test]
    fn unweighted_vertex_is_stationary_in_local_space() {
        let mut bird = fixture();
        bird.phase = std::f32::consts::FRAC_PI_2;
        let mut corner = [0., 0., 0.25, 0., 1., 0.];
        assert_eq!(bird.wing_z(&corner), 0.25);
        corner[5] = 0.5;
        assert!((bird.wing_z(&corner) - 0.75).abs() < 1e-6);
    }
    fn sample_scene() -> Scene {
        Scene::load(std::path::Path::new(
            &std::env::var("OPENJADE_FLIGHT_SCENE").expect("Set OPENJADE_FLIGHT_SCENE"),
        ))
        .unwrap()
    }
    fn capture(name: &str) -> Vec<u8> {
        let directory =
            std::env::var("OPENJADE_FLIGHT_CAPTURES").expect("Set OPENJADE_FLIGHT_CAPTURES");
        std::fs::read(std::path::Path::new(&directory).join(name)).unwrap()
    }
    fn float(data: &[u8], offset: usize) -> f32 {
        f32::from_le_bytes(data[offset..offset + 4].try_into().unwrap())
    }
    fn scale(row: &[u8]) -> f32 {
        dot(
            [float(row, 12), float(row, 28), float(row, 44)],
            [float(row, 12), float(row, 28), float(row, 44)],
        )
        .sqrt()
    }
    #[test]
    #[ignore = "Requires original GOG flight matrices and prepared scene"]
    fn gog_turns() {
        let mut scene = sample_scene();
        let camera = scene.camera;
        let flight = scene.flight.as_mut().unwrap();
        let data = capture("flight-paths-all.bin");
        assert_eq!(data.len() % 76, 0);
        for bird in &mut flight.birds {
            let mut seconds = 0.;
            let mut frames = 0;
            let mut turns = 0;
            let mut max_error = 0_f32;
            let mut worst_angle = 0_f32;
            let instance_scale = bird.scale;
            for row in data
                .as_chunks::<76>()
                .0
                .iter()
                .filter(|r| (scale(r.as_slice()) - instance_scale).abs() < 0.0001)
            {
                assert_eq!(u32::from_le_bytes(row[0..4].try_into().unwrap()), frames);
                let dt = float(row, 8);
                if frames > 0 {
                    seconds += dt;
                    if seconds > 50. {
                        break;
                    }
                    let before = bird.target;
                    bird.step(dt);
                    turns += usize::from(before != bird.target);
                }
                frames += 1;
                let center = [float(row, 24), float(row, 40), float(row, 56)];
                let world: V = std::array::from_fn(|i| {
                    camera[i] + camera[3 + i] * center[0] - camera[6 + i] * center[1]
                        + camera[9 + i] * center[2]
                });
                let delta = difference(world, bird.position);
                max_error = max_error.max(dot(delta, delta).sqrt());
                let column = [float(row, 16), float(row, 32), float(row, 48)];
                let measured = direction(std::array::from_fn(|i| {
                    -(camera[3 + i] * column[0] - camera[6 + i] * column[1]
                        + camera[9 + i] * column[2])
                }));
                worst_angle = worst_angle.max(
                    dot(measured, bird.heading)
                        .clamp(-1., 1.)
                        .acos()
                        .to_degrees(),
                );
            }
            println!("Speed {}: {frames} frames, {turns} switches, max position error {max_error}, max heading error {worst_angle} degrees",bird.speed);
            assert!(seconds >= 50. && turns >= 6 && max_error < 0.15 && worst_angle < 2.);
        }
    }
    #[test]
    #[ignore = "Requires original GOG wing vertex buffers and prepared scene"]
    fn gog_wings() {
        let mut scene = sample_scene();
        let flight = scene.flight.as_mut().unwrap();
        let data = capture("flight-study-all.bin");
        const RECORD: usize = 76 + 66 * 36;
        assert_eq!(data.len() % RECORD, 0);
        for bird in &mut flight.birds {
            let mut count = 0;
            let mut worst = 0_f32;
            let mut sq = 0_f64;
            let instance_scale = bird.scale;
            for row in data
                .as_chunks::<RECORD>()
                .0
                .iter()
                .filter(|r| (scale(r.as_slice()) - instance_scale).abs() < 0.0001)
            {
                let frame = u32::from_le_bytes(row[0..4].try_into().unwrap());
                if frame >= 2000 {
                    continue;
                }
                assert_eq!(frame as usize, count / 66);
                bird.step(float(row, 8));
                for (i, local) in flight.mesh.iter().enumerate() {
                    let off = 76 + i * 36;
                    assert_eq!(float(row, off), local[0]);
                    assert_eq!(float(row, off + 4), local[1]);
                    assert_eq!(float(row, off + 28), local[3]);
                    assert_eq!(float(row, off + 32), local[4]);
                    let error = (bird.wing_z(local) - float(row, off + 8)).abs();
                    worst = worst.max(error);
                    sq += f64::from(error).powi(2);
                    count += 1;
                }
            }
            println!(
                "Speed {}: {count} corners, maximum local Z error {worst}, RMS {}",
                bird.speed,
                (sq / count as f64).sqrt()
            );
            assert!(count == 132000 && worst < 0.01 && (sq / count as f64).sqrt() < 0.0002);
        }
    }
}
