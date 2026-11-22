//! Optional measured normal-projected reflection for one actor draw.
use crate::{invalid, Scene};
use std::io;
#[derive(Clone, Copy)]
pub struct Reflection {
    pub first: usize,
    pub count: usize,
    pub layer: usize,
    pub tint: [f32; 3],
}
impl Reflection {
    pub fn decode(data: &[u8], scene: &Scene) -> io::Result<Self> {
        if data.len() != 32 || &data[..8] != b"OJREFL01" {
            return Err(invalid("Invalid reflection sidecar"));
        }
        let word = |at| u32::from_le_bytes(data[at..at + 4].try_into().unwrap());
        let value = Self {
            first: word(8) as usize,
            count: word(12) as usize,
            layer: word(16) as usize,
            tint: std::array::from_fn(|i| f32::from_bits(word(20 + i * 4))),
        };
        if value.layer >= scene.layers as usize
            || value.count == 0
            || !scene.draws.iter().any(|d| {
                d.first as usize == value.first && d.count as usize == value.count && d.blend == 0
            })
            || value
                .tint
                .iter()
                .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
            || !scene
                .actor
                .as_ref()
                .is_some_and(|a| a.has_reflection_normals(value.first, value.count))
        {
            return Err(invalid("Unsupported reflection range, texture or normals"));
        }
        Ok(value)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Scene {
        let mut bytes = b"OJSCN002".to_vec();
        for x in [3u32, 1, 1, 1] {
            bytes.extend(x.to_le_bytes());
        }
        for x in [0f32, 0., 0., 1., 0., 0., 0., 1., 0., 0., 0., 1., 60.] {
            bytes.extend(x.to_le_bytes());
        }
        for _ in 0..3 {
            for x in [0f32, 0., 2., 0., 0., 1., 1., 1., 0.] {
                bytes.extend(x.to_le_bytes());
            }
        }
        bytes.extend([255; 4]);
        for x in [1u32, 0, 3, 0, 1] {
            bytes.extend(x.to_le_bytes());
        }
        for x in [1f32, 1., 0., 0., 1., 2., 0., 1.] {
            bytes.extend(x.to_le_bytes());
        }
        let mut scene = Scene::decode(&bytes).unwrap();
        let mut actor = b"OJACT001".to_vec();
        for x in [1u32, 0, 3] {
            actor.extend(x.to_le_bytes());
        }
        for x in [1f32, 1.] {
            actor.extend(x.to_le_bytes());
        }
        actor.extend((-1i32).to_le_bytes());
        for i in 0..16 {
            actor.extend((if i % 5 == 0 { 1f32 } else { 0. }).to_le_bytes());
        }
        for index in 0u32..3 {
            for x in [index, 1, 0] {
                actor.extend(x.to_le_bytes());
            }
            for x in [1f32, 0., 0., 0.] {
                actor.extend(x.to_le_bytes());
            }
        }
        let mut actor = crate::actor::Actor::decode(&actor, 3).unwrap();
        let mut light = b"OJALIT01".to_vec();
        light.extend(3u32.to_le_bytes());
        for i in 0..31 {
            light.extend((if i == 3 || i == 9 { 1f32 } else { 0. }).to_le_bytes());
        }
        for _ in 0..3 {
            light.extend(1u32.to_le_bytes());
            for x in [1f32, 0., 0.] {
                light.extend(x.to_le_bytes());
            }
        }
        actor.load_lighting(&light).unwrap();
        scene.actor = Some(actor);
        scene
    }
    #[test]
    fn reflection_requires_complete_opaque_actor_draw_and_bounded_texture() {
        let scene = fixture();
        let mut bytes = b"OJREFL01".to_vec();
        for x in [0u32, 3, 0] {
            bytes.extend(x.to_le_bytes());
        }
        for x in [0.25f32, 0.3, 0.4] {
            bytes.extend(x.to_le_bytes());
        }
        assert!(Reflection::decode(&bytes, &scene).is_ok());
        for length in 0..bytes.len() {
            assert!(Reflection::decode(&bytes[..length], &scene).is_err());
        }
        let mut extra = bytes.clone();
        extra.push(0);
        assert!(Reflection::decode(&extra, &scene).is_err());
        for (offset, value) in [(8, 1u32), (12, 2), (16, 1), (20, f32::NAN.to_bits())] {
            let mut bad = bytes.clone();
            bad[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
            assert!(Reflection::decode(&bad, &scene).is_err());
        }
        let mut scene = scene;
        scene.draws[0].blend = 1;
        assert!(Reflection::decode(&bytes, &scene).is_err());
        scene.draws[0].blend = 0;
        scene.actor = None;
        assert!(Reflection::decode(&bytes, &scene).is_err());
    }
}
