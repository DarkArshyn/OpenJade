//! Bounded reader for the local research interchange format, not a native Jade decoder.
use std::{
    io::{self, Read},
    path::Path,
};

#[derive(Clone, Debug)]
pub struct Draw {
    pub first: u32,
    pub count: u32,
    /// 0 = opaque, 1 = source-over, 6 = source-alpha additive.
    pub blend: u32,
    /// UV scale/offset, alpha, RGB gain, alpha cutoff, sampler (0/1/2).
    pub parameters: [f32; 8],
}
pub struct Scene {
    /// Packed world XYZ, native UV, diagnostic RGB, texture-array layer (nine floats).
    pub vertices: Vec<f32>,
    pub width: u32,
    pub height: u32,
    pub layers: u32,
    pub pixels: Vec<u8>,
    /// Position, right, up, forward (three floats each), vertical FOV in degrees.
    pub camera: [f32; 13],
    pub draws: Vec<Draw>,
}
fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, message)
}
impl Scene {
    pub fn load(path: &Path) -> io::Result<Self> {
        let file = std::fs::File::open(path)?;
        if file.metadata()?.len() > 256 * 1024 * 1024 {
            return Err(invalid("Scene exceeds 256 MiB"));
        }
        let mut bytes = Vec::new();
        file.take(256 * 1024 * 1024 + 1).read_to_end(&mut bytes)?;
        Self::decode(&bytes)
    }
    pub fn decode(bytes: &[u8]) -> io::Result<Self> {
        if bytes.len() < 76 || (&bytes[..8] != b"OJSCN001" && &bytes[..8] != b"OJSCN002") {
            return Err(invalid("Invalid scene header/version"));
        }
        let version2 = &bytes[..8] == b"OJSCN002";
        let word = |offset| u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap());
        let (count, width, height, layers) = (word(8), word(12), word(16), word(20));
        if count == 0
            || count > 1_000_000
            || count % 3 != 0
            || width == 0
            || height == 0
            || width > 2048
            || height > 2048
            || layers == 0
            || layers > 128
        {
            return Err(invalid("Invalid scene counts/dimensions"));
        }
        let vertex_end = 76u64 + u64::from(count) * 36;
        let expected = vertex_end + u64::from(width) * u64::from(height) * u64::from(layers) * 4;
        if expected > 256 * 1024 * 1024
            || expected > bytes.len() as u64
            || bytes.len() > 256 * 1024 * 1024
            || (!version2 && expected != bytes.len() as u64)
        {
            return Err(invalid("Scene extent mismatch"));
        }
        let floats = |data: &[u8]| -> Vec<f32> {
            data.as_chunks::<4>()
                .0
                .iter()
                .map(|b| f32::from_le_bytes(*b))
                .collect()
        };
        let camera: [f32; 13] = floats(&bytes[24..76]).try_into().unwrap();
        if !camera.iter().all(|f| f.is_finite()) || !(1.0..179.0).contains(&camera[12]) {
            return Err(invalid("Invalid camera/FOV"));
        }
        for a in 0..3 {
            let axis = &camera[3 + a * 3..6 + a * 3];
            let norm: f32 = axis.iter().map(|v| v * v).sum();
            if (norm - 1.0).abs() > 0.01 {
                return Err(invalid("Non-unit camera basis"));
            }
            for b in 0..a {
                let dot: f32 = axis
                    .iter()
                    .zip(&camera[3 + b * 3..6 + b * 3])
                    .map(|(x, y)| x * y)
                    .sum();
                if dot.abs() > 0.01 {
                    return Err(invalid("Non-orthogonal camera basis"));
                }
            }
        }
        let vertices = floats(&bytes[76..vertex_end as usize]);
        for triangle in vertices.as_chunks::<27>().0 {
            let layer = triangle[8];
            for vertex in triangle.as_chunks::<9>().0 {
                if !vertex.iter().all(|f| f.is_finite())
                    || vertex[8] != layer
                    || layer.fract() != 0.0
                    || layer < 0.0
                    || layer >= layers as f32
                {
                    return Err(invalid("Invalid vertex or texture layer"));
                }
            }
        }
        let mut draws = Vec::new();
        if version2 {
            let end = expected as usize;
            if bytes.len() < end + 4 {
                return Err(invalid("Missing draw table"));
            }
            let count = word(end) as usize;
            if count == 0 || count > 100_000 || end + 4 + count * 48 != bytes.len() {
                return Err(invalid("Invalid draw table extent"));
            }
            let mut cursor = 0u32;
            for i in 0..count {
                let base = end + 4 + i * 48;
                let (first, count, blend, write) =
                    (word(base), word(base + 4), word(base + 8), word(base + 12));
                let parameters: [f32; 8] = floats(&bytes[base + 16..base + 48]).try_into().unwrap();
                if first != cursor
                    || count == 0
                    || count % 3 != 0
                    || first
                        .checked_add(count)
                        .is_none_or(|end| end > vertices.len() as u32 / 9)
                    || !matches!((blend, write), (0, 1) | (1, 0) | (6, 0))
                    || !parameters.iter().all(|f| f.is_finite())
                    || !(0.0..=1.0).contains(&parameters[4])
                    || !(0.0..=2.0).contains(&parameters[5])
                    || !(0.0..=1.0).contains(&parameters[6])
                    || ![0., 1., 2.].contains(&parameters[7])
                {
                    return Err(invalid("Invalid draw state/range"));
                }
                cursor += count;
                draws.push(Draw {
                    first,
                    count,
                    blend,
                    parameters,
                });
            }
            if cursor != vertices.len() as u32 / 9 {
                return Err(invalid("Incomplete draw coverage"));
            }
        } else {
            draws.push(Draw {
                first: 0,
                count,
                blend: 0,
                parameters: [1., 1., 0., 0., 1., 1., 0.5, 0.],
            });
        }
        Ok(Self {
            vertices,
            width,
            height,
            layers,
            camera,
            pixels: bytes[vertex_end as usize..expected as usize].to_vec(),
            draws,
        })
    }
    /// Five vec4 push constants. Vulkan's positive-height viewport requires negative view Y.
    pub fn camera_constants(&self, aspect: f32) -> [f32; 20] {
        let mut p = [0.; 20];
        for i in 0..4 {
            p[i * 4..i * 4 + 3].copy_from_slice(&self.camera[i * 3..i * 3 + 3]);
        }
        p[16] = 1. / (self.camera[12].to_radians() * 0.5).tan();
        p[17] = aspect;
        p[18] = 0.1;
        p[19] = 1000.;
        p
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<u8> {
        let mut b = b"OJSCN001".to_vec();
        for v in [3u32, 1, 1, 1] {
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
        b.extend([255u8; 4]);
        b
    }
    #[test]
    fn accepts_bounded_triangle() {
        let s = Scene::decode(&fixture()).unwrap();
        assert_eq!(s.vertices.len(), 27);
        assert_eq!(s.pixels, [255; 4]);
    }
    #[test]
    fn rejects_truncated_and_trailing_data() {
        let b = fixture();
        assert!(Scene::decode(&b[..b.len() - 1]).is_err());
        let mut b = b;
        b.push(0);
        assert!(Scene::decode(&b).is_err());
    }
    #[test]
    fn rejects_counts_and_layers() {
        let mut b = fixture();
        b[8..12].copy_from_slice(&u32::MAX.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
        let mut b = fixture();
        b[108..112].copy_from_slice(&1f32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
    }
    #[test]
    fn rejects_invalid_camera_and_vertices() {
        let mut b = fixture();
        b[36..40].copy_from_slice(&0f32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
        let mut b = fixture();
        b[76..80].copy_from_slice(&f32::NAN.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
    }
    #[test]
    fn perspective_maps_near_and_far_to_vulkan_depth() {
        let s = Scene::decode(&fixture()).unwrap();
        let c = s.camera_constants(4. / 3.);
        let (n, f) = (c[18], c[19]);
        for (z, expected) in [(n, 0.), (f, 1.)] {
            let depth = (f * z / (f - n) - f * n / (f - n)) / z;
            assert!((depth - expected).abs() < 1e-5);
        }
        assert!((c[16] - 3f32.sqrt()).abs() < 1e-5);
    }
}

#[cfg(test)]
mod material_tests {
    use super::*;
    fn package() -> Vec<u8> {
        let mut b = b"OJSCN002".to_vec();
        for v in [3u32, 1, 1, 1] {
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
        b.extend([255u8; 4]);
        b.extend(1u32.to_le_bytes());
        for v in [0u32, 3, 1, 0] {
            b.extend(v.to_le_bytes());
        }
        for v in [1f32, 1., 0., 0., 1., 1., 0., 2.] {
            b.extend(v.to_le_bytes());
        }
        b
    }
    #[test]
    fn reads_transparent_draw() {
        let s = Scene::decode(&package()).unwrap();
        assert_eq!(s.draws[0].blend, 1);
        assert_eq!(s.draws[0].parameters[7], 2.);
        assert_eq!(s.pixels.len(), 4);
    }
    #[test]
    fn rejects_unsupported_blend_depth_and_sampler() {
        for (offset, word) in [(200, 3u32), (204, 1), (236, 3f32.to_bits())] {
            let mut b = package();
            b[offset..offset + 4].copy_from_slice(&word.to_le_bytes());
            assert!(Scene::decode(&b).is_err());
        }
    }
    #[test]
    fn rejects_uncovered_or_truncated_draws() {
        let b = package();
        assert!(Scene::decode(&b[..b.len() - 1]).is_err());
        let mut b = b;
        b[192..196].copy_from_slice(&3u32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
    }
}
