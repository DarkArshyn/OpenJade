//! OpenJade-owned live settings bridge; never writes original game settings.
use std::{
    io::{self, Read},
    path::Path,
};
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct GraphicsSettings {
    pub preview: u8,
    pub saved: u8,
}
impl GraphicsSettings {
    pub fn parse(text: &str) -> Option<Self> {
        if text.len() > 64 {
            return None;
        }
        let mut lines = text.lines();
        if lines.next()? != "OJSET001" {
            return None;
        }
        let preview = lines.next()?;
        let saved = lines.next()?;
        if preview.is_empty()
            || saved.is_empty()
            || !preview.bytes().all(|c| c.is_ascii_digit())
            || !saved.bytes().all(|c| c.is_ascii_digit())
        {
            return None;
        }
        let preview = preview.parse::<u8>().ok()?;
        let saved = saved.parse::<u8>().ok()?;
        if preview > 100 || saved > 100 || lines.next().is_some() {
            return None;
        }
        Some(Self { preview, saved })
    }
    pub fn load(path: &Path) -> io::Result<Self> {
        let mut text = String::new();
        std::fs::File::open(path)?
            .take(65)
            .read_to_string(&mut text)?;
        Self::parse(&text).ok_or_else(|| {
            io::Error::new(
                io::ErrorKind::InvalidData,
                "Invalid OJSET001 graphics settings",
            )
        })
    }
}
/// Reconstruct the bounded native ramp. f32 stores mirror observed x87 stores;
/// exp uses the standard library rather than copying the original CRT routine.
pub fn gamma_ramp(value: u8) -> [u16; 256] {
    let normalized = f32::from(value.min(100)) / 100.;
    let gain = f64::from(normalized * 0.5).exp() as f32;
    std::array::from_fn(|i| {
        let scaled = (f64::from(gain) * i as f64 * 255.) as f32;
        scaled.min(65535.).trunc() as u16
    })
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn strict_settings() {
        assert_eq!(
            GraphicsSettings::parse("OJSET001\n42\n10\n"),
            Some(GraphicsSettings {
                preview: 42,
                saved: 10
            })
        );
        for s in [
            "OJSET002\n0\n0",
            "OJSET001\n101\n0",
            "OJSET001\n-1\n0",
            "OJSET001\n0\n0\nextra",
            "OJSET001\n0",
        ] {
            assert!(GraphicsSettings::parse(s).is_none());
        }
    }
    #[test]
    fn zero_is_native_ramp_not_identity() {
        let r = gamma_ramp(0);
        for (i, v) in r.iter().enumerate() {
            assert_eq!(*v, i as u16 * 255);
        }
        assert_eq!(r[255], 65025);
    }
    #[test]
    fn ramps_are_monotonic_and_saturate() {
        let mut previous = gamma_ramp(0);
        for gamma in 1..=100 {
            let r = gamma_ramp(gamma);
            assert_eq!(r[0], 0);
            assert!(r.windows(2).all(|x| x[0] <= x[1]));
            assert!(r.iter().zip(previous).all(|(a, b)| *a >= b));
            previous = r;
        }
        assert_eq!(previous[255], 65535);
        assert_eq!(previous[128], 53814);
    }
}
