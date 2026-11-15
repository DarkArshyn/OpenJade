//! CPU-only diagnostic: excludes Vulkan, presentation and frame pacing.
use jade_assets::actor::Actor;
use std::{hint::black_box, path::PathBuf, time::Instant};
fn main() {
    let path = PathBuf::from(std::env::args().nth(1).expect("actor path"));
    let bytes = std::fs::read(&path).unwrap();
    let count = u32::from_le_bytes(bytes[16..20].try_into().unwrap()) as usize;
    for mode in ["skin", "sheath", "lit"] {
        let start = Instant::now();
        let mut actor = Actor::decode(&bytes, count).unwrap();
        if mode != "skin" {
            actor
                .load_sheath(&std::fs::read(path.with_extension("sheath")).unwrap())
                .unwrap();
        }
        if mode == "lit" {
            actor
                .load_lighting(&std::fs::read(path.with_extension("actorlight")).unwrap())
                .unwrap();
        }
        println!(
            "{mode} load_ms={:.3}",
            start.elapsed().as_secs_f64() * 1000.
        );
        for time in [0., 0.5, 2., 3.9] {
            for _ in 0..3 {
                black_box(actor.render_vertices(time));
            }
            let mut samples = Vec::new();
            for _ in 0..25 {
                let start = Instant::now();
                black_box(actor.render_vertices(black_box(time)));
                samples.push(start.elapsed().as_secs_f64() * 1000.);
            }
            samples.sort_by(f64::total_cmp);
            println!(
                "{mode} t={time} median_ms={:.3} p95_ms={:.3}",
                samples[12], samples[23]
            );
        }
    }
}
