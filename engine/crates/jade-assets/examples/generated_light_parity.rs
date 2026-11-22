//! Compare the production calculation with private native Camera02 samples.
use jade_assets::actor::generated_direction;
use std::path::PathBuf;
fn float(bytes: &[u8], at: usize) -> f32 {
    f32::from_le_bytes(bytes[at..at + 4].try_into().unwrap())
}
fn main() {
    let root = PathBuf::from(std::env::args().nth(1).expect("capture folder"));
    let name = root.file_name().unwrap().to_str().unwrap();
    let reference = std::fs::read(root.join(format!("{name}-reference.bin"))).unwrap();
    let native = std::fs::read(root.join(format!("{name}-direction.bin"))).unwrap();
    assert_eq!(reference.len() % 32, 0);
    assert_eq!(native.len() % 44, 0);
    assert_eq!(reference.len() / 32, native.len() / 44);
    let mut max_error = 0f32;
    for (r, n) in reference
        .as_chunks::<32>()
        .0
        .iter()
        .zip(native.as_chunks::<44>().0)
    {
        assert_eq!(&r[..8], &n[..8]);
        let owner = std::array::from_fn(|i| float(r, 8 + 4 * i));
        let camera = std::array::from_fn(|i| float(r, 20 + 4 * i));
        let actual = generated_direction(owner, camera).unwrap();
        for (i, value) in actual.iter().enumerate() {
            max_error = max_error.max((value - float(n, 24 + 4 * i)).abs());
        }
    }
    assert_eq!(reference.len() / 32, 3025);
    assert!(max_error < 3e-7);
    println!(
        "samples={} maximum_direction_error={max_error}",
        reference.len() / 32
    );
}
