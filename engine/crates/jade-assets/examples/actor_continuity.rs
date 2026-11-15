//! Measure diagnostic loop displacement; this is not native animation parity.
use jade_assets::actor::Actor;
use std::path::PathBuf;
fn main() {
    let path = PathBuf::from(std::env::args().nth(1).expect("actor path"));
    let data = std::fs::read(&path).unwrap();
    let count = u32::from_le_bytes(data[16..20].try_into().unwrap()) as usize;
    for with_sheath in [false, true] {
        println!("sheath={with_sheath}");
        let mut actor = Actor::decode(&data, count).unwrap();
        if with_sheath {
            actor
                .load_sheath(&std::fs::read(path.with_extension("sheath")).unwrap())
                .unwrap();
        }
        for (a, b) in [
            (0., 1. / 60.),
            (2., 2. + 1. / 60.),
            (4. - 1. / 60., 4.),
            (4. - 0.00001, 4.),
        ] {
            let p = actor.positions(a);
            let q = actor.positions(b);
            let mut largest = (0usize, 0f32);
            let mut sum = 0.;
            for ((index, x), (_, y)) in p.iter().zip(&q) {
                let d = (0..3).map(|j| (x[j] - y[j]).powi(2)).sum::<f32>().sqrt();
                assert!(d.is_finite());
                sum += d * d;
                if d > largest.1 {
                    largest = (*index, d);
                }
            }
            println!(
                "from={a:.6} to={b:.6} max_distance={:.9} vertex={} rms={:.9}",
                largest.1,
                largest.0,
                (sum / count as f32).sqrt()
            );
        }
    }
}
