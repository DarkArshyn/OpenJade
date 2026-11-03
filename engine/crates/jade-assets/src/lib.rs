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
    /// 0 disables fog, 1 uses the normal GOG range, 2 inverts it.
    /// Runtime rain adds 4 to enable per-vertex alpha (not an OJSCN file flag).
    pub vertex_fog: u32,
    /// UV scale/offset, alpha, RGB gain, alpha cutoff, sampler (0/1/2).
    pub parameters: [f32; 8],
}
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub enum TextureFilter {
    Nearest,
    #[default]
    Linear,
    Trilinear,
}
#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub enum ColorPipeline {
    #[default]
    Srgb,
    LegacyUnorm,
}
pub mod curtain_field;
pub mod native_mips;
pub mod palms;
pub mod rain;
pub mod rido2;
pub struct Scene {
    pub rain: Option<rain::Rain>,
    pub glow: Option<(u32, u8)>,
    pub menu_additive: bool,
    pub trunk_mips: Option<native_mips::TrunkMips>,
    pub leaf: Option<(usize, usize, Vec<u8>)>,
    pub curtains: Vec<rido2::Curtain>,
    pub palms: Vec<palms::PalmVertex>,
    /// Diagnostic choice, not a recovered original runtime state.
    pub color_pipeline: ColorPipeline,
    /// Enables the measured menu blur when native menu sidecars and UNORM are used.
    pub menu_blur: bool,
    /// Actual base-level dimensions inside each transport slot.
    pub texture_sizes: Vec<[u32; 2]>,
    /// First UI texture; UI filtering is independent of scene filtering.
    pub ui_start: u32,
    pub filter: TextureFilter,
    /// Packed world XYZ, native UV, diagnostic RGB, texture-array layer (nine floats).
    pub vertices: Vec<f32>,
    pub width: u32,
    pub height: u32,
    pub layers: u32,
    pub pixels: Vec<u8>,
    /// Position, right, up, forward (three floats each), vertical FOV in degrees.
    pub camera: [f32; 13],
    pub draws: Vec<Draw>,
    /// Per-pass UV cycles per second; zero for legacy packages.
    pub uv_rates: Vec<[f32; 2]>,
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
        let mut scene = Self::decode(&bytes)?;
        for extension in ["rido1", "rido2", "rido3", "rido4"] {
            match std::fs::File::open(path.with_extension(extension)) {
                Ok(file) => {
                    let mut control = Vec::new();
                    file.take(1393).read_to_end(&mut control)?;
                    scene
                        .curtains
                        .push(rido2::Curtain::decode(&control, &scene.vertices)?);
                }
                Err(e) if e.kind() == io::ErrorKind::NotFound => {}
                Err(e) => return Err(e),
            }
        }
        if let Some(draw) = scene.draws.iter().find(|d| d.blend == 7) {
            let mut leaf = Vec::new();
            std::fs::File::open(path.with_extension("leaf"))?
                .take(11113)
                .read_to_end(&mut leaf)?;
            let first = draw.first as usize;
            let layer = scene.vertices[first * 9 + 8] as usize;
            if leaf.len() != 11112
                || &leaf[..8] != b"OJLEAF01"
                || leaf[8..12] != draw.first.to_le_bytes()
                || leaf[12..16] != (layer as u32).to_le_bytes()
                || draw.count != 216
                || scene.texture_sizes[layer] != [128, 64]
                || scene.vertices[first * 9..(first + 216) * 9]
                    .as_chunks::<9>()
                    .0
                    .iter()
                    .any(|v| v[8] as usize != layer)
                || scene.draws.iter().filter(|d| d.blend == 7).count() != 1
            {
                return Err(invalid("Invalid leaf sidecar"));
            }
            scene.leaf = Some((first, layer, leaf.split_off(16)));
        }
        match std::fs::File::open(path.with_extension("trunk")) {
            Ok(file) => {
                let mut bytes = Vec::new();
                file.take(349457).read_to_end(&mut bytes)?;
                let mip = native_mips::TrunkMips::decode(&bytes, &scene.texture_sizes)?;
                if mip.rgba[..262144] != scene.texture_pixels(mip.layer) {
                    return Err(invalid("Trunk base mip differs from scene texture"));
                }
                scene.trunk_mips = Some(mip);
            }
            Err(e) if e.kind() == io::ErrorKind::NotFound => {}
            Err(e) => return Err(e),
        }
        match std::fs::File::open(path.with_extension("glow")) {
            Ok(file) => {
                let mut bytes = Vec::new();
                file.take(21).read_to_end(&mut bytes)?;
                if bytes.len() != 20 || &bytes[..8] != b"OJGLOW01" {
                    return Err(invalid("Invalid glow sidecar"));
                }
                let first = u32::from_le_bytes(bytes[8..12].try_into().unwrap());
                let count = u32::from_le_bytes(bytes[12..16].try_into().unwrap());
                let alpha = u32::from_le_bytes(bytes[16..20].try_into().unwrap());
                if count != 72
                    || alpha > 255
                    || !scene
                        .draws
                        .iter()
                        .any(|d| d.first == first && d.count == count && d.blend == 0)
                {
                    return Err(invalid("Invalid glow draw binding"));
                }
                scene.glow = Some((first, alpha as u8));
            }
            Err(e) if e.kind() == io::ErrorKind::NotFound => {}
            Err(e) => return Err(e),
        }
        match std::fs::File::open(path.with_extension("rain")) {
            Ok(file) => {
                let mut bytes = Vec::new();
                file.take(4417).read_to_end(&mut bytes)?;
                rain::Rain::attach(&mut scene, &bytes)?;
            }
            Err(e) if e.kind() == io::ErrorKind::NotFound => {}
            Err(e) => return Err(e),
        }
        Ok(scene)
    }
    pub fn decode(bytes: &[u8]) -> io::Result<Self> {
        let mut palm_bytes = &[][..];
        let bytes = if bytes.starts_with(b"OJSCN005") {
            if !(80..=256 * 1024 * 1024).contains(&bytes.len()) {
                return Err(invalid("Invalid palm scene extent"));
            }
            let end = bytes.len() - 4;
            let count = u32::from_le_bytes(bytes[end..].try_into().unwrap()) as usize;
            if count == 0 || count > 1_000_000 || end < 76 + count * 44 {
                return Err(invalid("Invalid palm count"));
            }
            let start = end - count * 44;
            palm_bytes = &bytes[start..end];
            &bytes[..start]
        } else {
            bytes
        };
        if bytes.len() < 76
            || (&bytes[..8] != b"OJSCN001"
                && &bytes[..8] != b"OJSCN002"
                && &bytes[..8] != b"OJSCN003"
                && &bytes[..8] != b"OJSCN004"
                && &bytes[..8] != b"OJSCN005")
        {
            return Err(invalid("Invalid scene header/version"));
        }
        let version4 = &bytes[..8] == b"OJSCN004" || &bytes[..8] == b"OJSCN005";
        let version3 = version4 || &bytes[..8] == b"OJSCN003";
        let version2 = version3 || &bytes[..8] == b"OJSCN002";

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
        let mut texture_sizes = vec![[width, height]; layers as usize];
        let mut draws = Vec::new();
        let mut uv_rates = Vec::new();
        if version2 {
            let end = expected as usize;
            if bytes.len() < end + 4 {
                return Err(invalid("Missing draw table"));
            }
            let count = word(end) as usize;
            if count == 0
                || count > 100_000
                || end
                    + 4
                    + count * 48
                    + if version3 { layers as usize * 8 } else { 0 }
                    + if version4 { count * 8 } else { 0 }
                    != bytes.len()
            {
                return Err(invalid("Invalid draw table extent"));
            }
            if version3 {
                for (i, size) in texture_sizes.iter_mut().enumerate() {
                    let offset = end + 4 + count * 48 + i * 8;
                    *size = [word(offset), word(offset + 4)];
                    if size[0] == 0 || size[1] == 0 || size[0] > width || size[1] > height {
                        return Err(invalid("Invalid native texture dimensions"));
                    }
                }
            }
            if version4 {
                let start = end + 4 + count * 48 + layers as usize * 8;
                for pair in bytes[start..].as_chunks::<8>().0 {
                    let rate: [f32; 2] = floats(pair).try_into().unwrap();
                    if rate.iter().any(|r| !r.is_finite() || r.abs() > 1024.) {
                        return Err(invalid("Invalid UV rate"));
                    }
                    uv_rates.push(rate);
                }
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
                    || !matches!(
                        (blend, write),
                        (0, 1 | 3 | 5) | (7, 0 | 2 | 4) | (1, 0) | (6, 0)
                    )
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
                    vertex_fog: write >> 1,
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
                vertex_fog: 0,
                parameters: [1., 1., 0., 0., 1., 1., 0.5, 0.],
            });
        }
        if !version4 {
            uv_rates = vec![[0.; 2]; draws.len()];
        }
        Ok(Self {
            leaf: None,
            trunk_mips: None,
            curtains: Vec::new(),
            palms: palms::decode(palm_bytes, &vertices)?,
            uv_rates,
            texture_sizes,
            ui_start: layers,
            filter: TextureFilter::default(),
            color_pipeline: ColorPipeline::default(),
            menu_blur: true,
            rain: None,
            glow: None,
            menu_additive: true,
            vertices,
            width,
            height,
            layers,
            camera,
            pixels: bytes[vertex_end as usize..expected as usize].to_vec(),
            draws,
        })
    }
    /// Extract rows without resampling or including transport padding.
    pub fn texture_pixels(&self, layer: usize) -> Vec<u8> {
        let [w, h] = self.texture_sizes[layer];
        let start = layer * self.width as usize * self.height as usize * 4;
        (0..h as usize)
            .flat_map(|y| {
                let stride = if layer >= self.ui_start as usize {
                    w
                } else {
                    self.width
                };
                let row = start + y * stride as usize * 4;
                self.pixels[row..row + w as usize * 4].iter().copied()
            })
            .collect()
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
    fn palm_trailer_rejects_invalid_vertex_and_count() {
        let mut b = package();
        b[..8].copy_from_slice(b"OJSCN005");
        b.extend(1u32.to_le_bytes());
        b.extend(1u32.to_le_bytes());
        b.extend([0u8; 8]);
        let record = b.len();
        b.extend([0u8; 44]);
        b.extend(1u32.to_le_bytes());
        assert_eq!(Scene::decode(&b).unwrap().palms.len(), 1);
        b[record..record + 4].copy_from_slice(&3u32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
        b.truncate(record + 43);
        assert!(Scene::decode(&b).is_err());
    }
    #[test]
    fn validates_v4_motion_and_keeps_legacy_static() {
        let mut b = package();
        assert_eq!(Scene::decode(&b).unwrap().uv_rates, [[0.; 2]]);
        b[..8].copy_from_slice(b"OJSCN004");
        b.extend(1u32.to_le_bytes());
        b.extend(1u32.to_le_bytes());
        b.extend(0.125f32.to_le_bytes());
        b.extend((-0.25f32).to_le_bytes());
        assert_eq!(Scene::decode(&b).unwrap().uv_rates, [[0.125, -0.25]]);
        assert!(Scene::decode(&b[..b.len() - 1]).is_err());
        let mut trailing = b.clone();
        trailing.push(0);
        assert!(Scene::decode(&trailing).is_err());
        let n = b.len();
        for rate in [f32::NAN, f32::INFINITY, 1025.] {
            b[n - 4..].copy_from_slice(&rate.to_le_bytes());
            assert!(Scene::decode(&b).is_err());
        }
    }
    #[test]
    fn leaf_depth_is_tested_without_writes() {
        let mut b = package();
        let start = 76 + 3 * 36 + 4 + 4;
        b[start + 8..start + 12].copy_from_slice(&7u32.to_le_bytes());
        for flags in [0u32, 2, 4] {
            b[start + 12..start + 16].copy_from_slice(&flags.to_le_bytes());
            assert_eq!(Scene::decode(&b).unwrap().draws[0].vertex_fog, flags >> 1);
        }
        for flags in [1u32, 3, 5] {
            b[start + 12..start + 16].copy_from_slice(&flags.to_le_bytes());
            assert!(Scene::decode(&b).is_err());
        }
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

pub mod ui;

#[cfg(test)]
mod native_texture_tests {
    use super::*;
    #[test]
    fn crops_transport_rows_without_resampling() {
        let s = Scene {
            vertices: vec![],
            width: 3,
            height: 2,
            layers: 1,
            pixels: (0u8..24).collect(),
            camera: [0.; 13],
            leaf: None,
            trunk_mips: None,
            curtains: Vec::new(),
            palms: vec![],
            uv_rates: vec![],
            draws: vec![],
            texture_sizes: vec![[2, 2]],
            ui_start: 1,
            filter: TextureFilter::Linear,
            color_pipeline: ColorPipeline::default(),
            menu_blur: true,
            rain: None,
            glow: None,
            menu_additive: true,
        };
        assert_eq!(
            s.texture_pixels(0),
            [0, 1, 2, 3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19]
        );
    }
    #[test]
    fn validates_v3_dimensions_and_extent() {
        let mut b = b"OJSCN003".to_vec();
        for v in [3u32, 2, 1, 1] {
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
        b.extend([10, 20, 30, 40, 0, 0, 0, 0]);
        for v in [1u32, 0, 3, 0, 1] {
            b.extend(v.to_le_bytes());
        }
        for v in [1f32, 1., 0., 0., 1., 1., 0.5, 0.] {
            b.extend(v.to_le_bytes());
        }
        b.extend(1u32.to_le_bytes());
        b.extend(1u32.to_le_bytes());
        let s = Scene::decode(&b).unwrap();
        assert_eq!(s.texture_sizes, [[1, 1]]);
        assert_eq!(s.texture_pixels(0), [10, 20, 30, 40]);
        assert!(Scene::decode(&b[..b.len() - 1]).is_err());
        let n = b.len();
        b[n - 8..n - 4].copy_from_slice(&3u32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
        b[n - 8..n - 4].copy_from_slice(&0u32.to_le_bytes());
        assert!(Scene::decode(&b).is_err());
    }
}

pub mod settings;

pub mod native_ui;
