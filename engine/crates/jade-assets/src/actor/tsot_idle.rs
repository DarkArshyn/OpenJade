//! Bounded TSoT menu idle sequence, specified from resource and GOG observations.
//! This is not a general actor behavior interpreter.
use super::{slerp, Actor, Matrix, Track};
use std::cell::Cell;

pub(super) struct Idle {
    pub tracks: Vec<Track>,
    pub duration: f64,
    pub activated: Cell<Option<f64>>,
}
#[derive(Debug, PartialEq)]
struct Phase {
    alternative: bool,
    tick: f64,
    previous_alternative: bool,
    blend: f32,
    retained: bool,
}
impl Idle {
    fn phase(&self, seconds: f64, base_duration: f64, base_rate: f64) -> Phase {
        let normal = || Phase {
            alternative: false,
            tick: (seconds * base_rate) % base_duration,
            previous_alternative: false,
            blend: 1.,
            retained: false,
        };
        let Some(start) = self.activated.get() else {
            return normal();
        };
        if seconds < start {
            return normal();
        }
        // Activation enables decisions at clip end; it does not restart the playing clip.
        let end = ((start * base_rate / base_duration).floor() + 1.) * base_duration / base_rate;
        if seconds < end {
            return normal();
        }
        let mut elapsed = seconds - end;
        let mut previous = false;
        let mut retained = false;
        // The measured row runs two action-24 cycles, three action-1 cycles, then
        // remains in stage 3. Durations derive from clip data and observed rates.
        for (alternative, repeats, rate) in [(true, 2, 10.), (false, 3, 10.)] {
            let duration = if alternative {
                self.duration
            } else {
                base_duration
            };
            for _ in 0..repeats {
                if elapsed < duration / rate {
                    return Phase {
                        alternative,
                        tick: elapsed * rate,
                        previous_alternative: previous,
                        blend: if alternative { 1. } else { blend(elapsed) },
                        retained,
                    };
                }
                elapsed -= duration / rate;
                retained |= alternative;
                previous = alternative;
            }
        }
        Phase {
            alternative: true,
            tick: (elapsed * 5.) % self.duration,
            previous_alternative: true,
            blend: 1.,
            retained: true,
        }
    }
    pub fn local(&self, actor: &Actor, seconds: f64) -> Vec<Matrix> {
        let phase = self.phase(seconds, actor.duration as f64, actor.rate as f64);
        let mut local: Vec<_> = actor.bones.iter().map(|b| b.local).collect();
        if phase.retained {
            for t in &self.tracks {
                if !actor
                    .tracks
                    .iter()
                    .any(|base| base.bone == t.bone && base.rotation == t.rotation)
                {
                    apply(&mut local, t, t.sample(self.duration as f32));
                }
            }
        }
        let incoming = if phase.alternative {
            &self.tracks
        } else {
            &actor.tracks
        };
        let outgoing = if phase.previous_alternative {
            &self.tracks
        } else {
            &actor.tracks
        };
        let end = if phase.previous_alternative {
            self.duration as f32
        } else {
            actor.duration
        };
        for t in incoming {
            let mut value = t.sample(phase.tick as f32);
            if phase.blend < 1. {
                if let Some(old) = outgoing
                    .iter()
                    .find(|old| old.bone == t.bone && old.rotation == t.rotation)
                {
                    let a = old.sample(end);
                    value = if t.rotation {
                        slerp(a, value, phase.blend)
                    } else {
                        std::array::from_fn(|i| a[i] + (value[i] - a[i]) * phase.blend)
                    };
                }
            }
            apply(&mut local, t, value);
        }
        local
    }
}
fn apply(local: &mut [Matrix], track: &Track, value: [f32; 4]) {
    if track.rotation {
        for (i, row) in super::quaternion(value).iter().enumerate() {
            local[track.bone][i][..3].copy_from_slice(row);
        }
    } else {
        local[track.bone][3][..3].copy_from_slice(&value[..3]);
    }
}
fn blend(seconds: f64) -> f32 {
    // Fixed 125 Hz simulation shares the sheath timebase, independent of presentation.
    // Native elapsed storage truncates to 1/15360 second at each update.
    let steps = (seconds * 125.).floor();
    let elapsed = steps * 122. / 15360. + (seconds - steps / 125.);
    (elapsed / (11. / 60.)).min(1.) as f32
}
#[cfg(test)]
mod tests {
    use super::*;
    fn idle() -> Idle {
        Idle {
            tracks: vec![],
            duration: 73.,
            activated: Cell::new(Some(9.)),
        }
    }
    #[test]
    fn sequence_uses_clip_end_and_terminal_stage() {
        let i = idle();
        assert!(!i.phase(11.99, 20., 5.).alternative);
        assert_eq!(i.phase(12., 20., 5.).tick, 0.);
        assert!(i.phase(19.31, 20., 5.).alternative);
        let p = i.phase(26.61, 20., 5.);
        assert!(!p.alternative && p.previous_alternative && p.retained);
        assert!(i.phase(32.61, 20., 5.).alternative);
        assert!(i.phase(32.6 + 3. * 14.6 + 0.01, 20., 5.).alternative);
    }
    #[test]
    fn sampling_is_independent_of_display_order() {
        let i = idle();
        let expected = i.phase(28.7, 20., 5.);
        for rate in [30, 60, 144, 240] {
            for frame in 0..rate * 30 {
                let _ = i.phase(frame as f64 / rate as f64, 20., 5.);
            }
            assert_eq!(i.phase(28.7, 20., 5.), expected);
        }
        assert_eq!(blend(0.), 0.);
        assert_eq!(blend(0.2), 1.);
    }
}
