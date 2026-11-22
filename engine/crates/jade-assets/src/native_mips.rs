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

/// Five independently read-back-verified levels for the 128x64 sword base texture.
pub struct SwordMips {
    pub layer: usize,
    pub rgba: Vec<u8>,
}
impl SwordMips {
    pub fn decode(bytes: &[u8], sizes: &[[u32; 2]], base: &[u8]) -> io::Result<Self> {
        if bytes.len() != 43664 || &bytes[..8] != b"OJSWMP01" {
            return Err(super::invalid("Invalid sword mip extent or signature"));
        }
        let layer = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
        if sizes.get(layer) != Some(&[128, 64])
            || bytes[12..16] != 5u32.to_le_bytes()
            || base != &bytes[16..32784]
        {
            return Err(super::invalid("Invalid sword mip binding, levels or base"));
        }
        Ok(Self {
            layer,
            rgba: bytes[16..].to_vec(),
        })
    }
}
#[cfg(test)]
mod sword_tests {
    use super::*;
    #[test]
    fn sword_chain_has_exact_extent_and_matching_base() {
        let mut bytes = b"OJSWMP01".to_vec();
        bytes.extend(0u32.to_le_bytes());
        bytes.extend(5u32.to_le_bytes());
        for (i, (w, h)) in [(128, 64), (64, 32), (32, 16), (16, 8), (8, 4)]
            .into_iter()
            .enumerate()
        {
            bytes.extend(vec![i as u8; w * h * 4]);
        }
        let sizes = [[128, 64]];
        let base = vec![0; 32768];
        let parsed = SwordMips::decode(&bytes, &sizes, &base).unwrap();
        assert_eq!(&parsed.rgba[43520..], vec![4; 128]);
        for length in [0, 8, 16, bytes.len() - 1] {
            assert!(SwordMips::decode(&bytes[..length], &sizes, &base).is_err());
        }
        assert!(SwordMips::decode(&bytes, &[[128, 128]], &base).is_err());
        assert!(SwordMips::decode(&bytes, &sizes, &vec![1; 32768]).is_err());
        bytes.push(0);
        assert!(SwordMips::decode(&bytes, &sizes, &base).is_err());
    }
}
