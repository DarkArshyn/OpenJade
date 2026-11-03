//! Local material clock; independent of camera playback and swapchain rebuilds.
pub(super) fn parameters(mut p: [f32; 8], rate: [f32; 2], elapsed: f64) -> [f32; 8] {
    for axis in 0..2 {
        if rate[axis] != 0. {
            p[axis + 2] =
                (f64::from(p[axis + 2]) + f64::from(rate[axis]) * elapsed).rem_euclid(1.) as f32;
        }
    }
    p
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn signed_motion_preserves_static_components() {
        let p = [2., 3., 0.25, 0.75, 0.5, 2., 0., 2.];
        let a = parameters(p, [0.125, -0.25], 3.);
        assert_eq!(a, [2., 3., 0.625, 0., 0.5, 2., 0., 2.]);
        assert_eq!(parameters(p, [0.; 2], 1e9), p);
        assert_eq!(parameters(p, [0.125, -0.25], 0.), p);
    }
    #[test]
    fn wrap_and_absolute_time_are_stable() {
        let p = [1., 1., 0., 0., 1., 1., 0., 1.];
        assert_eq!(parameters(p, [0.125, -0.25], 8.), p);
        assert_eq!(parameters(p, [0.125, 0.], 8_000_003.)[2], 0.375);
    }
}
