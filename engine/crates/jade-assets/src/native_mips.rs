//! Bounded native BC1 mip chain exported from the frozen menu texture.
use std::io;

pub struct TrunkMips {
    pub layer: usize,
    pub rgba: Vec<u8>,
}
impl TrunkMips {
    pub fn decode(bytes: &[u8], sizes: &[[u32; 2]]) -> io::Result<Self> {
        if bytes.len() != 349456 || &bytes[..8] != b"OJTRNK01" {
            return Err(super::invalid("Invalid trunk mip extent or signature"));
        }
        let layer = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
        if sizes.get(layer) != Some(&[256, 256]) || bytes[12..16] != 6u32.to_le_bytes() {
            return Err(super::invalid("Invalid trunk mip binding or level count"));
        }
        Ok(Self {
            layer,
            rgba: bytes[16..].to_vec(),
        })
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Vec<u8> {
        let mut bytes = b"OJTRNK01".to_vec();
        bytes.extend(0u32.to_le_bytes());
        bytes.extend(6u32.to_le_bytes());
        for (level, size) in [256, 128, 64, 32, 16, 8].into_iter().enumerate() {
            bytes.extend(vec![level as u8; size * size * 4]);
        }
        bytes
    }
    #[test]
    fn preserves_each_native_level() {
        let m = TrunkMips::decode(&fixture(), &[[256, 256]]).unwrap();
        let mut pos = 0;
        for (level, size) in [256, 128, 64, 32, 16, 8].into_iter().enumerate() {
            assert!(m.rgba[pos..pos + size * size * 4]
                .iter()
                .all(|&v| v == level as u8));
            pos += size * size * 4;
        }
        assert_eq!(pos, m.rgba.len());
    }
    #[test]
    fn rejects_truncated_extra_and_wrong_binding() {
        let b = fixture();
        for n in [0, 8, 16, b.len() - 1] {
            assert!(TrunkMips::decode(&b[..n], &[[256, 256]]).is_err());
        }
        let mut extra = b.clone();
        extra.push(0);
        assert!(TrunkMips::decode(&extra, &[[256, 256]]).is_err());
        assert!(TrunkMips::decode(&b, &[]).is_err());
        assert!(TrunkMips::decode(&b, &[[128, 128]]).is_err());
        let mut bad = b;
        bad[12] = 7;
        assert!(TrunkMips::decode(&bad, &[[256, 256]]).is_err());
    }
}
