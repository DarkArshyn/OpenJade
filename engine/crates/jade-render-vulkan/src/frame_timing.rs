//! Opt-in bounded timings; CPU present calls do not measure display scanout.
use std::time::Instant;
pub(super) fn gpu_ms(ticks: [u64; 2], bits: u32, period: f32) -> f64 {
    let mask = u64::MAX >> (64 - bits);
    (ticks[1].wrapping_sub(ticks[0]) & mask) as f64 * f64::from(period) / 1e6
}
pub(super) struct Timing {
    pub vsync: Option<bool>,
    limit: usize,
    frames: usize,
    previous: Option<Instant>,
    cpu: Vec<[f64; 7]>,
    gpu: Vec<f64>,
    keep_gpu: bool,
}
impl Timing {
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let limit = std::env::var("OPENJADE_PROFILE_FRAMES")
            .ok()
            .map(|s| s.parse::<usize>())
            .transpose()?
            .unwrap_or(0);
        if limit != 0 && !(60..=6000).contains(&limit) {
            return Err("OPENJADE_PROFILE_FRAMES must be 60..6000".into());
        }
        let vsync = match std::env::var("OPENJADE_PROFILE_PRESENT").ok().as_deref() {
            None => None,
            Some("fifo") if limit > 0 => Some(true),
            Some("immediate") if limit > 0 => Some(false),
            _ => {
                return Err(
                    "OPENJADE_PROFILE_PRESENT requires profiling and fifo or immediate".into(),
                )
            }
        };
        Ok(Self {
            vsync,
            limit,
            frames: 0,
            previous: None,
            cpu: Vec::new(),
            gpu: Vec::new(),
            keep_gpu: false,
        })
    }
    pub fn enabled(&self) -> bool {
        self.limit > 0
    }
    pub fn complete(&self) -> bool {
        self.enabled() && self.frames >= self.limit
    }
    pub fn gpu(&mut self, ms: f64) {
        if self.keep_gpu {
            self.gpu.push(ms);
        }
    }
    pub fn frame(&mut self, t: [Instant; 7], rebuilt: bool) {
        if !self.enabled() {
            return;
        }
        self.frames += 1;
        self.keep_gpu = self.frames > 30 && !rebuilt && self.cpu.len() < 6000;
        let previous = self.previous;
        self.previous = if rebuilt { None } else { Some(t[0]) };
        self.keep_gpu &= previous.is_some();
        if self.keep_gpu {
            let mut row = [0.; 7];
            row[0] = previous.map_or(0., |p| (t[0] - p).as_secs_f64() * 1000.);
            for i in 0..6 {
                row[i + 1] = (t[i + 1] - t[i]).as_secs_f64() * 1000.;
            }
            self.cpu.push(row);
        }
    }
    pub fn report(&self) {
        if !self.enabled() {
            return;
        }
        fn stats(label: &str, mut v: Vec<f64>) {
            if v.is_empty() {
                println!("Timing {label}: unavailable");
                return;
            }
            v.sort_by(f64::total_cmp);
            let n = v.len();
            println!(
                "Timing {label}: n={n} median={:.3} p95={:.3} max={:.3} ms",
                v[n / 2],
                v[(n * 95).div_ceil(100) - 1],
                v[n - 1]
            );
        }
        for (i, label) in [
            "frame_interval",
            "simulation",
            "fence",
            "acquire",
            "record_upload",
            "submit",
            "present_call",
        ]
        .iter()
        .enumerate()
        {
            stats(label, self.cpu.iter().map(|r| r[i]).collect());
        }
        stats("gpu_commands", self.gpu.clone());
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn timestamps_wrap_at_queue_valid_bits() {
        assert_eq!(gpu_ms([250, 5], 8, 1000.), 0.011);
        assert_eq!(gpu_ms([u64::MAX - 4, 5], 64, 1000.), 0.01);
    }
}
