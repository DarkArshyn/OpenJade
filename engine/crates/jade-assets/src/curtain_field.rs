//! Spatial interpolation weight used by the menu curtain deformation component.
use std::sync::OnceLock;

struct Field {
    permutation: [usize; 256],
    gradients: [[f32; 2]; 256],
}

impl Field {
    fn new() -> Self {
        let mut state = 1u32;
        let mut next = || {
            state = state.wrapping_mul(214013).wrapping_add(2531011);
            (state >> 16) & 32767
        };
        let mut permutation = std::array::from_fn(|i| i);
        let gradients = std::array::from_fn(|_| {
            // The shared generator also initializes one- and three-dimensional fields.
            next();
            let [x, y] = std::array::from_fn(|_| (next() % 512) as f32 - 256.0);
            let length = (x * x + y * y).sqrt();
            for _ in 0..3 {
                next();
            }
            [x / length, y / length]
        });
        for i in (1..256).rev() {
            permutation.swap(i, (next() % 256) as usize);
        }
        Self {
            permutation,
            gradients,
        }
    }
}

/// Samples the field after the caller has applied spatial scale and phase.
pub fn curtain_weight(x: f32, y: f32) -> f32 {
    static TABLE: OnceLock<Field> = OnceLock::new();
    let field = TABLE.get_or_init(Field::new);
    let [x, y] = [x, y].map(|v| v + 4096.0);
    let [i, j] = [x, y].map(|v| (v as i32 & 255) as usize);
    let [u, v] = [x, y].map(|v| f64::from(v.fract()));
    let corner = |a: usize, b: usize| {
        let index = (field.permutation[(i + a) & 255] + j + b) & 255;
        let [gx, gy] = field.gradients[field.permutation[index]].map(f64::from);
        (gx * (u - a as f64) + gy * (v - b as f64)) as f32
    };
    let fade = |t: f64| (t * t * (3.0 - 2.0 * t)) as f32;
    let mix = |a: f32, b: f32, t: f32| f64::from(a) + (f64::from(b) - f64::from(a)) * f64::from(t);
    let lower = mix(corner(0, 0), corner(1, 0), fade(u)) as f32;
    let upper = mix(corner(0, 1), corner(1, 1), fade(u)) as f32;
    let noise = mix(lower, upper, fade(v));
    ((1.0 + noise) * 0.5) as f32
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn matches_x86_curtain_point_five() {
        for (x, y, weight) in [
            (0x3f0803ef, 0x3e494793, 0x3e9800f6),
            (0x3f54d0bc, 0x3efe3d63, 0x3ec98a4b),
            (0x3f90cec4, 0x3f4beb7e, 0x3eeac1cd),
            (0x3fdd9b91, 0x3fb2c28c, 0x3f0ffff0),
        ] {
            assert_eq!(
                curtain_weight(f32::from_bits(x), f32::from_bits(y)).to_bits(),
                weight
            );
        }
    }
}
