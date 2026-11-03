//! Camera-relative pass ordering for static research geometry.
use jade_assets::Draw;

pub(super) struct DrawOrder {
    centers: Vec<[f64; 3]>,
}

impl DrawOrder {
    /// Inputs come from a validated Scene; UI vertices are outside its draw ranges.
    pub(super) fn new(vertices: &[f32], draws: &[Draw]) -> Self {
        let centers = draws
            .iter()
            .map(|draw| {
                let mut center = [0.; 3];
                let start = draw.first as usize * 9;
                let end = start + draw.count as usize * 9;
                for vertex in vertices[start..end].as_chunks::<9>().0 {
                    for axis in 0..3 {
                        center[axis] += f64::from(vertex[axis]);
                    }
                }
                center.map(|sum| sum / f64::from(draw.count))
            })
            .collect();
        Self { centers }
    }

    /// Same eye/forward constants as scene.vert. Opaque order is preserved;
    /// equal-depth transparent stages retain their original relative order.
    pub(super) fn indices(&self, draws: &[Draw], camera: &[f32; 20]) -> Vec<usize> {
        let depth: Vec<f64> = self
            .centers
            .iter()
            .map(|center| {
                (0..3)
                    .map(|axis| {
                        (center[axis] - f64::from(camera[axis])) * f64::from(camera[12 + axis])
                    })
                    .sum()
            })
            .collect();
        let mut indices: Vec<usize> = (0..draws.len()).collect();
        indices.sort_by(|&a, &b| {
            let phase = |blend| match blend {
                0 => 0,
                7 => 1,
                _ => 2,
            };
            let transparent_a = phase(draws[a].blend);
            let transparent_b = phase(draws[b].blend);
            transparent_a.cmp(&transparent_b).then_with(|| {
                if transparent_a == 2 && transparent_b == 2 {
                    depth[b].total_cmp(&depth[a]).then(a.cmp(&b))
                } else {
                    a.cmp(&b)
                }
            })
        });
        indices
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn leaf_follows_opaque_and_precedes_fog() {
        let (v, d) = fixture(&[(7, [0., 0., 1.]), (1, [0., 0., 4.]), (0, [0., 0., 8.])]);
        let order = DrawOrder::new(&v, &d);
        let mut camera = [0.; 20];
        camera[14] = 1.;
        assert_eq!(order.indices(&d, &camera), vec![2, 0, 1]);
    }
    fn fixture(rows: &[(u32, [f32; 3])]) -> (Vec<f32>, Vec<Draw>) {
        let mut vertices = Vec::new();
        let mut draws = Vec::new();
        for &(blend, position) in rows {
            draws.push(Draw {
                first: (vertices.len() / 9) as u32,
                count: 3,
                blend,
                vertex_fog: 0,
                parameters: [1.; 8],
            });
            for _ in 0..3 {
                vertices.extend(position);
                vertices.extend([0.; 6]);
            }
        }
        (vertices, draws)
    }

    fn camera(forward: [f32; 3]) -> [f32; 20] {
        let mut c = [0.; 20];
        c[12..15].copy_from_slice(&forward);
        c
    }

    #[test]
    fn rotation_reverses_transparent_order_and_reset_restores_it() {
        let (v, d) = fixture(&[(1, [0., 0., 2.]), (1, [0., 0., 8.])]);
        let order = DrawOrder::new(&v, &d);
        let initial = camera([0., 0., 1.]);
        assert_eq!(order.indices(&d, &initial), [1, 0]);
        assert_eq!(order.indices(&d, &camera([0., 0., -1.])), [0, 1]);
        assert_eq!(order.indices(&d, &initial), [1, 0]);
    }

    #[test]
    fn opaque_first_and_equal_depth_stages_remain_stable() {
        let (v, d) = fixture(&[
            (6, [0., 0., 5.]),
            (0, [0., 0., 2.]),
            (1, [0., 0., 5.]),
            (0, [0., 0., 9.]),
        ]);
        let order = DrawOrder::new(&v, &d);
        assert_eq!(order.indices(&d, &camera([0., 0., 1.])), [1, 3, 0, 2]);
    }

    #[test]
    fn uses_view_depth_not_euclidean_distance() {
        let (v, d) = fixture(&[(1, [100., 0., 1.]), (1, [0., 0., 5.])]);
        let order = DrawOrder::new(&v, &d);
        let mut c = camera([0., 0., 1.]);
        c[2] = 3.;
        assert_eq!(order.indices(&d, &c), [1, 0]);
    }

    #[test]
    fn center_uses_each_draw_range_and_ignores_trailing_ui() {
        let (mut v, d) = fixture(&[(1, [1., 2., 3.]), (1, [7., 8., 9.])]);
        v[9] = 4.;
        v.extend([999.; 27]);
        let order = DrawOrder::new(&v, &d);
        assert_eq!(order.centers, [[2., 2., 3.], [7., 8., 9.]]);
        assert!(DrawOrder::new(&[], &[])
            .indices(&[], &camera([0., 0., 1.]))
            .is_empty());
    }
}
