//! Local menu bundle and deterministic prototype navigation. No original game logic.
use crate::Scene;
use std::{io, path::Path};
#[derive(Clone)]
pub struct Button {
    pub action: u32,
    pub rect: [f32; 4],
}
pub struct Page {
    pub buttons: Vec<Button>,
    pub first_frame: u32,
}
pub struct Menu {
    pub pages: Vec<Page>,
    pub page: usize,
    pub focus: Option<usize>,
    pub pressed: Option<usize>,
    pub time: Option<f32>,
    pub first_vertex: u32,
    pub cameras: Vec<[f32; 13]>,
    return_page: usize,
}
fn bad() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "Invalid/incompatible UI bundle")
}
impl Menu {
    pub fn load(path: &Path, scene: &mut Scene) -> io::Result<Self> {
        use std::io::Read;
        let file = std::fs::File::open(path)?;
        if file.metadata()?.len() > 128 * 1024 * 1024 {
            return Err(bad());
        }
        let mut bytes = Vec::new();
        file.take(128 * 1024 * 1024 + 1).read_to_end(&mut bytes)?;
        Self::decode(&bytes, scene)
    }
    pub fn decode(bytes: &[u8], scene: &mut Scene) -> io::Result<Self> {
        let mut input = bytes;
        fn take<'a>(input: &mut &'a [u8], n: usize) -> io::Result<&'a [u8]> {
            if input.len() < n {
                return Err(bad());
            }
            let (a, b) = input.split_at(n);
            *input = b;
            Ok(a)
        }
        fn word(input: &mut &[u8]) -> io::Result<u32> {
            Ok(u32::from_le_bytes(take(input, 4)?.try_into().unwrap()))
        }
        fn number(input: &mut &[u8]) -> io::Result<f32> {
            let f = f32::from_bits(word(input)?);
            if !f.is_finite() {
                return Err(bad());
            }
            Ok(f)
        }
        if take(&mut input, 8)? != b"OJUI0001"
            || word(&mut input)? != 5
            || scene.width != 512
            || scene.height != 512
        {
            return Err(bad());
        }
        let mut pages = Vec::new();
        let mut frames = 0;
        for _ in 0..5 {
            let count = word(&mut input)?;
            if count == 0 || count > 8 {
                return Err(bad());
            }
            let mut buttons = Vec::new();
            for _ in 0..count {
                let action = word(&mut input)?;
                let mut rect = [0.; 4];
                for v in &mut rect {
                    *v = number(&mut input)?;
                }
                if action > 8
                    || rect[0] >= rect[2]
                    || rect[1] >= rect[3]
                    || rect[0] < 0.
                    || rect[1] < 0.
                    || rect[2] > 805.
                    || rect[3] > 605.
                {
                    return Err(bad());
                }
                buttons.push(Button { action, rect });
            }
            pages.push(Page {
                buttons,
                first_frame: frames,
            });
            frames += count + 1;
        }
        let layers = word(&mut input)?;
        if layers != frames * 4 || scene.layers + layers > 128 {
            return Err(bad());
        }
        let pixels = take(&mut input, layers as usize * 512 * 512 * 4)?;
        if word(&mut input)? != 541 {
            return Err(bad());
        }
        let mut cameras = Vec::new();
        for _ in 0..541 {
            let mut camera = [0.; 13];
            for v in &mut camera {
                *v = number(&mut input)?;
            }
            if !(1.0..179.0).contains(&camera[12]) {
                return Err(bad());
            }
            for i in 0..3 {
                let norm: f32 = camera[3 + i * 3..6 + i * 3].iter().map(|v| v * v).sum();
                if (norm - 1.).abs() > 0.01 {
                    return Err(bad());
                }
            }
            cameras.push(camera);
        }
        if !input.is_empty()
            || cameras[0]
                .iter()
                .zip(scene.camera)
                .any(|(a, b)| (a - b).abs() > 0.001)
        {
            return Err(bad());
        }
        let first_vertex = (scene.vertices.len() / 9) as u32;
        for layer in 0..layers {
            let x = (layer % 2) * 512;
            let y = ((layer % 4) / 2) * 512;
            for (u, v) in [(0., 0.), (1., 0.), (1., 1.), (0., 0.), (1., 1.), (0., 1.)] {
                scene.vertices.extend([
                    ((x as f32 + u * 512.) / 400.) - 1.,
                    ((y as f32 + v * 512.) / 300.) - 1.,
                    0.,
                    u,
                    v,
                    1.,
                    1.,
                    1.,
                    (scene.layers + layer) as f32,
                ]);
            }
        }
        scene
            .texture_sizes
            .extend(vec![[512, 512]; layers as usize]);
        scene.pixels.extend_from_slice(pixels);
        scene.layers += layers;
        Ok(Self {
            pages,
            page: 0,
            focus: None,
            pressed: None,
            time: None,
            first_vertex,
            cameras,
            return_page: 0,
        })
    }
    pub fn vertex(&self) -> Option<u32> {
        self.time.is_none().then(|| {
            self.first_vertex
                + (self.pages[self.page].first_frame + self.focus.map_or(0, |i| i as u32 + 1)) * 24
        })
    }
    pub fn camera(&self) -> [f32; 13] {
        self.cameras[(self.time.unwrap_or(0.).clamp(0., 9.) * 60.).floor() as usize]
    }
    pub fn tick(&mut self, seconds: f32) {
        if let Some(time) = &mut self.time {
            *time = (*time + seconds.max(0.)).min(9.);
        }
    }
    pub fn hit(&self, x: f32, y: f32) -> Option<usize> {
        if self.time.is_some() {
            return None;
        }
        self.pages[self.page]
            .buttons
            .iter()
            .position(|b| x >= b.rect[0] && y >= b.rect[1] && x < b.rect[2] && y < b.rect[3])
    }
    pub fn navigate(&mut self, delta: i32) {
        if self.time.is_none() {
            let n = self.pages[self.page].buttons.len() as i32;
            self.focus = Some(
                (self
                    .focus
                    .map_or(if delta > 0 { -1 } else { 0 }, |i| i as i32)
                    + delta)
                    .rem_euclid(n) as usize,
            );
            self.pressed = None;
        }
    }
    fn show(&mut self, page: usize) {
        self.page = page;
        self.focus = None;
        self.pressed = None;
    }
    pub fn quit_prompt(&mut self) {
        if self.page == 3 {
            return;
        }
        self.return_page = self.page;
        self.time = None;
        self.show(3);
    }
    pub fn escape(&mut self) {
        if self.time.take().is_some() {
            self.show(0);
        } else if self.page == 3 {
            self.show(self.return_page);
        } else if self.page == 0 {
            self.quit_prompt();
        } else {
            self.show(0);
        }
    }
    pub fn activate(&mut self) -> bool {
        if self.time.is_some() {
            return false;
        }
        let Some(index) = self.focus else {
            return false;
        };
        match self.pages[self.page].buttons[index].action {
            0 => {
                self.time = Some(0.);
                self.pressed = None;
            }
            1 => self.show(1),
            2 => self.show(2),
            3 => self.quit_prompt(),
            4 | 6 => {
                self.return_page = self.page;
                self.show(4);
            }
            5 => self.show(if self.page == 4 { self.return_page } else { 0 }),
            7 => return true,
            8 => self.show(self.return_page),
            _ => {}
        }
        false
    }
}
/// A shared 4:3 viewport keeps rendering and input coordinates in agreement.
pub fn viewport(width: u32, height: u32) -> [f32; 4] {
    let scale = (width as f32 / 800.).min(height as f32 / 600.);
    [
        (width as f32 - 800. * scale) / 2.,
        (height as f32 - 600. * scale) / 2.,
        800. * scale,
        600. * scale,
    ]
}
#[cfg(test)]
mod tests {
    use super::*;
    fn menu() -> Menu {
        Menu {
            pages: vec![
                Page {
                    buttons: vec![
                        Button {
                            action: 0,
                            rect: [0., 0., 10., 10.],
                        },
                        Button {
                            action: 3,
                            rect: [20., 0., 30., 10.],
                        },
                    ],
                    first_frame: 0,
                },
                Page {
                    buttons: vec![],
                    first_frame: 3,
                },
                Page {
                    buttons: vec![],
                    first_frame: 4,
                },
                Page {
                    buttons: vec![Button {
                        action: 8,
                        rect: [0., 0., 10., 10.],
                    }],
                    first_frame: 5,
                },
                Page {
                    buttons: vec![],
                    first_frame: 7,
                },
            ],
            page: 0,
            focus: None,
            pressed: None,
            time: None,
            first_vertex: 100,
            cameras: vec![[0.; 13]; 541],
            return_page: 0,
        }
    }
    #[test]
    fn transition_clamps_and_resets() {
        let mut m = menu();
        m.navigate(1);
        assert!(!m.activate());
        m.tick(10.);
        assert_eq!(m.time, Some(9.));
        assert_eq!(m.vertex(), None);
        m.escape();
        assert_eq!(m.time, None);
        assert_eq!(m.page, 0);
    }
    #[test]
    fn quit_cancel_and_hit_bounds() {
        let mut m = menu();
        assert_eq!(m.hit(10., 5.), None);
        m.escape();
        assert_eq!(m.page, 3);
        m.focus = Some(0);
        assert!(!m.activate());
        assert_eq!(m.page, 0);
    }
    #[test]
    fn letterbox_coordinates() {
        assert_eq!(viewport(1600, 900), [200., 0., 1200., 900.]);
        assert_eq!(viewport(800, 800), [0., 100., 800., 600.]);
    }
}

#[cfg(test)]
mod invalid_bundle_tests {
    use super::*;
    #[test]
    fn malformed_bundle_does_not_mutate_scene() {
        let mut scene = Scene {
            texture_sizes: vec![[512, 512]],
            ui_start: 1,
            filter: Default::default(),
            color_pipeline: Default::default(),
            vertices: vec![],
            width: 512,
            height: 512,
            layers: 1,
            pixels: vec![],
            camera: [0.; 13],
            draws: vec![],
        };
        for bytes in [b"".as_slice(), b"OJUI0001", b"OJUI0001\x05\x00\x00\x00"] {
            assert!(Menu::decode(bytes, &mut scene).is_err());
            assert_eq!(scene.layers, 1);
            assert!(scene.vertices.is_empty());
        }
    }
}
