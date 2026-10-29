//! Independent native menu state and sprite composition. Game data stays read-only.
use crate::{ColorPipeline, Scene, TextureFilter};
use std::{
    collections::BTreeMap,
    io::{self, Read},
    path::Path,
};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Page {
    Create,
    Profiles,
    Main,
    Options,
    Keyboard,
    Gamepad,
    Game,
    Effects,
    Advanced,
    Sound,
    Credits,
}
#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    Route(Page),
    Back,
    Quit,
    Answer(u8),
    Default,
    Choice(usize, usize),
    Step(usize, i32),
    Slider(usize, f32, f32),
    Scroll(i32),
    Binding(bool, usize, usize),
    Create,
    Profile(usize),
    Delete,
    Select,
    New,
}
#[derive(Clone)]
pub struct Hit {
    pub action: Action,
    pub rect: [f32; 4],
}
#[derive(Clone, Copy)]
struct Sprite {
    layer: u32,
    rect: [f32; 4],
    metrics: [f32; 3],
    texture_size: [f32; 2],
}
#[derive(Clone, Debug, PartialEq)]
pub struct Settings {
    pub values: [usize; 20],
    pub keys: Vec<String>,
    pub pad: Vec<String>,
}
const DEFAULTS: [usize; 20] = [
    1, 0, 0, 1, 0, 0, 0, 0, 0, 2, 0, 100, 100, 100, 0, 0, 0, 43, 0, 0,
];
const MAX: [usize; 20] = [
    4, 100, 2, 1, 1, 2, 2, 1, 1, 3, 1, 100, 100, 100, 2, 1, 1, 100, 1, 1,
];
const KEYS: [&str; 36] = [
    "Z",
    "Up",
    "Q",
    "Left",
    "S",
    "Down",
    "D",
    "Right",
    "Shift",
    "Num Del",
    "Space",
    "Right Ctrl",
    "Mouse 2",
    "",
    "Mouse 1",
    "",
    "E",
    "Mouse 3",
    "C",
    "Num 1",
    "R",
    "Right Shift",
    "F",
    "Delete",
    "A",
    "End",
    "X",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
];
const ACTIONS: [&str; 18] = [
    "Move Forward",
    "Move Left",
    "Move Backward",
    "Move Right",
    "Walk Toggle",
    "Jump",
    "Special Action",
    "Sword Attack",
    "Use Dagger",
    "Cancel",
    "Rewind",
    "First Person View",
    "Alternate View",
    "Reset Camera",
    "Camera Forward",
    "Camera Backward",
    "Camera Left",
    "Camera Right",
];
impl Default for Settings {
    fn default() -> Self {
        let mut pad = vec![String::new(); 18];
        for (i, s) in ["Y Axis(+)", "X Axis(-)", "Y Axis(-)", "X Axis(+)", "", "B1"]
            .iter()
            .enumerate()
        {
            pad[i] = s.to_string();
        }
        Self {
            values: DEFAULTS,
            keys: KEYS.iter().map(|s| s.to_string()).collect(),
            pad,
        }
    }
}
/// Only confirmed preferences may cross the boundary into the renderer/window.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct AppliedDisplay {
    pub gamma: u8,
    pub filter: TextureFilter,
    pub resolution: (u32, u32),
    pub vsync: bool,
}
pub struct NativeMenu {
    sprites: BTreeMap<String, Sprite>,
    font_size: f32,
    font_sizes: Vec<u32>,
    pub pixel_scale: f32,
    srgb: bool,
    pub page: Page,
    modal: Option<u8>,
    destination: Page,
    pub focus: Option<usize>,
    pub pressed: Option<usize>,
    pub pointer: Option<(f32, f32)>,
    drag: Option<Action>,
    pub hits: Vec<Hit>,
    pub vertices: Vec<f32>,
    pub settings: Settings,
    pub saved: Settings,
    pub profiles: Vec<String>,
    pub selected: Option<usize>,
    pub active: Option<usize>,
    pub typed: String,
    binding: Option<(bool, usize, usize)>,
    offset: usize,
    pub time: Option<f32>,
    cameras: Vec<[f32; 13]>,
    pub error: String,
    pub save_requested: bool,
}
fn bad() -> io::Error {
    io::Error::new(io::ErrorKind::InvalidData, "Invalid native menu data")
}
struct Reader<'a>(&'a [u8]);
impl<'a> Reader<'a> {
    fn take(&mut self, n: usize) -> io::Result<&'a [u8]> {
        if self.0.len() < n {
            return Err(bad());
        }
        let (a, b) = self.0.split_at(n);
        self.0 = b;
        Ok(a)
    }
    fn word(&mut self) -> io::Result<u32> {
        Ok(u32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    fn float(&mut self) -> io::Result<f32> {
        let v = f32::from_bits(self.word()?);
        if !v.is_finite() {
            return Err(bad());
        }
        Ok(v)
    }
}
impl NativeMenu {
    pub fn load(path: &Path, scene: &mut Scene) -> io::Result<Self> {
        let mut bytes = Vec::new();
        std::fs::File::open(path)?
            .take(32 * 1024 * 1024 + 1)
            .read_to_end(&mut bytes)?;
        Self::decode(&bytes, scene)
    }
    pub fn decode(bytes: &[u8], scene: &mut Scene) -> io::Result<Self> {
        if bytes.len() > 32 * 1024 * 1024 || scene.width != 512 || scene.height != 512 {
            return Err(bad());
        }
        let mut r = Reader(bytes);
        let magic = r.take(8)?;
        let v3 = magic == b"OJUI0003";
        if !v3 && magic != b"OJUI0002" {
            return Err(bad());
        }
        let layers = r.word()?;
        let font_size = r.float()?;
        let count = r.word()?;
        if !(1..=16).contains(&layers)
            || scene.layers + layers > 128
            || !(1. ..=256.).contains(&font_size)
            || !(100..=2048).contains(&count)
        {
            return Err(bad());
        }
        let mut texture_sizes = vec![[512, 512]; layers as usize];
        let mut font_sizes = Vec::new();
        if v3 {
            for dims in &mut texture_sizes {
                *dims = [r.word()?, r.word()?];
                if dims.contains(&0)
                    || dims.iter().any(|v| *v > 2048)
                    || dims[0] * dims[1] > 512 * 512
                {
                    return Err(bad());
                }
            }
            let n = r.word()?;
            if n == 0 || n > 16 {
                return Err(bad());
            }
            for _ in 0..n {
                let size = r.word()?;
                if !(1..=128).contains(&size) || font_sizes.last().is_some_and(|s| *s >= size) {
                    return Err(bad());
                }
                font_sizes.push(size);
            }
        }
        let mut sprites = BTreeMap::new();
        for _ in 0..count {
            let n = r.word()? as usize;
            if n == 0 || n > 32 {
                return Err(bad());
            }
            let name = std::str::from_utf8(r.take(n)?)
                .map_err(|_| bad())?
                .to_owned();
            let layer = r.word()?;
            let x = r.word()?;
            let y = r.word()?;
            let w = r.word()?;
            let h = r.word()?;
            let metrics = [r.float()?, r.float()?, r.float()?];
            if layer >= layers {
                return Err(bad());
            }
            let [tw, th] = texture_sizes[layer as usize];
            if w == 0
                || h == 0
                || x > tw
                || y > th
                || w > tw - x
                || h > th - y
                || metrics.iter().any(|v| v.abs() > 512.)
            {
                return Err(bad());
            }
            if sprites
                .insert(
                    name,
                    Sprite {
                        layer: scene.layers + layer,
                        rect: [x as f32, y as f32, w as f32, h as f32],
                        metrics,
                        texture_size: [tw as f32, th as f32],
                    },
                )
                .is_some()
            {
                return Err(bad());
            }
        }
        for name in [
            "panel", "logo", "cursor", "eax", "field", "up", "down", "bar", "minus", "plus",
            "handle",
        ]
        .into_iter()
        .map(str::to_owned)
        .chain(if v3 {
            font_sizes
                .iter()
                .flat_map(|size| (32..127).map(move |c| format!("f{size}_c{c}")))
                .collect::<Vec<_>>()
        } else {
            (32..127).map(|c| format!("c{c}")).collect()
        }) {
            if !sprites.contains_key(&name) {
                return Err(bad());
            }
        }
        let pixels = r.take(layers as usize * 512 * 512 * 4)?;
        if r.word()? != 541 {
            return Err(bad());
        }
        let mut cameras = Vec::new();
        for _ in 0..541 {
            let mut c = [0.; 13];
            for v in &mut c {
                *v = r.float()?
            }
            if !(1. ..179.).contains(&c[12]) {
                return Err(bad());
            }
            for i in 0..3 {
                let norm: f32 = c[3 + i * 3..6 + i * 3].iter().map(|v| v * v).sum();
                if (norm - 1.).abs() > 0.01 {
                    return Err(bad());
                }
            }
            cameras.push(c);
        }
        if !r.0.is_empty()
            || cameras[0]
                .iter()
                .zip(scene.camera)
                .any(|(a, b)| (a - b).abs() > 0.001)
        {
            return Err(bad());
        }
        let mut settings = Settings::default();
        settings.values[2] = match scene.filter {
            TextureFilter::Trilinear => 0,
            TextureFilter::Linear => 1,
            TextureFilter::Nearest => 2,
        };
        let mut this = Self {
            sprites,
            font_size,
            font_sizes,
            pixel_scale: 1.,
            srgb: scene.color_pipeline == ColorPipeline::Srgb,
            page: Page::Create,
            modal: None,
            destination: Page::Main,
            focus: None,
            pressed: None,
            pointer: None,
            drag: None,
            hits: vec![],
            vertices: vec![],
            saved: settings.clone(),
            settings,
            profiles: vec![],
            selected: None,
            active: None,
            typed: String::new(),
            binding: None,
            offset: 0,
            time: None,
            cameras,
            error: String::new(),
            save_requested: false,
        };
        scene.texture_sizes.extend(texture_sizes);
        scene.pixels.extend_from_slice(pixels);
        scene.layers += layers;
        this.render();
        Ok(this)
    }
    pub fn camera(&self) -> [f32; 13] {
        self.cameras[(self.time.unwrap_or(0.).clamp(0., 9.) * 60.).floor() as usize]
    }
    pub fn tick(&mut self, dt: f32) {
        if let Some(t) = &mut self.time {
            *t = (*t + dt.max(0.)).min(9.)
        }
    }
    pub fn applied_display(&self) -> AppliedDisplay {
        let v = &self.saved.values;
        AppliedDisplay {
            gamma: v[1] as u8,
            filter: match v[2] {
                0 => TextureFilter::Trilinear,
                1 => TextureFilter::Linear,
                _ => TextureFilter::Nearest,
            },
            resolution: [
                (640, 480),
                (800, 600),
                (1024, 768),
                (1280, 960),
                (1600, 1200),
            ][v[0]],
            vsync: v[3] == 1,
        }
    }
    pub fn gamma(&self) -> u8 {
        self.settings.values[1] as u8
    }
    pub fn filter(&self) -> TextureFilter {
        match self.settings.values[2] {
            0 => TextureFilter::Trilinear,
            1 => TextureFilter::Linear,
            _ => TextureFilter::Nearest,
        }
    }
    pub fn resolution(&self) -> (u32, u32) {
        [
            (640, 480),
            (800, 600),
            (1024, 768),
            (1280, 960),
            (1600, 1200),
        ][self.settings.values[0]]
    }
    pub fn hit(&self, x: f32, y: f32) -> Option<usize> {
        self.hits
            .iter()
            .position(|h| x >= h.rect[0] && y >= h.rect[1] && x < h.rect[2] && y < h.rect[3])
    }
    pub fn navigate(&mut self, delta: i32) {
        if !self.hits.is_empty() {
            self.focus = Some(
                (self
                    .focus
                    .map_or(if delta > 0 { -1 } else { 0 }, |i| i as i32)
                    + delta)
                    .rem_euclid(self.hits.len() as i32) as usize,
            )
        }
    }
    pub fn motion(&mut self, x: f32, y: f32) {
        self.pointer = Some((x, y));
        self.focus = self.hit(x, y);
        if let Some(Action::Slider(i, a, b)) = self.drag {
            self.settings.values[i] =
                (((x - a) / (b - a)).clamp(0., 1.) * MAX[i] as f32).round() as usize;
        }
    }
    pub fn press(&mut self) {
        self.pressed = self.focus;
        if let Some(Hit {
            action: Action::Slider(i, a, b),
            ..
        }) = self.focus.and_then(|i| self.hits.get(i))
        {
            self.drag = Some(Action::Slider(*i, *a, *b));
            if let Some((x, y)) = self.pointer {
                self.motion(x, y)
            }
        }
    }
    pub fn release(&mut self) -> bool {
        self.drag = None;
        let p = self.pressed.take();
        if p.is_some() && p == self.focus {
            self.activate()
        } else {
            false
        }
    }
    pub fn unfocus(&mut self) {
        self.pressed = None;
        self.drag = None;
        self.pointer = None;
        self.focus = None;
    }
    fn show(&mut self, page: Page) {
        self.page = page;
        self.focus = None;
        self.pressed = None;
        self.drag = None;
        self.typed.clear();
        self.binding = None;
        self.error.clear();
        self.render();
    }
    pub fn quit_prompt(&mut self) {
        self.binding = None;
        self.modal = Some(1);
        self.focus = None;
        self.drag = None;
        self.pressed = None;
        self.render();
    }
    pub fn escape(&mut self) {
        if self.binding.take().is_some() {
            self.typed.clear();
            return;
        }
        if self.modal.take().is_some() {
            self.focus = None;
            self.render();
            return;
        }
        if self.time.take().is_some() {
            self.show(Page::Main);
            return;
        }
        if matches!(self.page, Page::Main | Page::Profiles)
            || self.page == Page::Create && self.profiles.is_empty()
        {
            self.quit_prompt();
            return;
        }
        let dest = match self.page {
            Page::Create => Page::Profiles,
            Page::Options | Page::Credits => Page::Main,
            _ => Page::Options,
        };
        if self.settings != self.saved {
            self.destination = dest;
            self.modal = Some(0);
            self.focus = None;
            self.render()
        } else {
            self.show(dest)
        }
    }
    pub fn adjust(&mut self, delta: i32) {
        if let Some(h) = self.focus.and_then(|i| self.hits.get(i)) {
            match h.action {
                Action::Slider(i, _, _) | Action::Step(i, _) => self.step(i, delta),
                _ => {}
            }
        }
    }
    fn step(&mut self, i: usize, d: i32) {
        self.settings.values[i] =
            (self.settings.values[i] as i32 + d).clamp(0, MAX[i] as i32) as usize;
    }
    pub fn scroll(&mut self, d: i32) {
        if matches!(self.page, Page::Keyboard | Page::Gamepad) && self.modal.is_none() {
            self.offset = (self.offset as i32 + d).clamp(0, 12) as usize;
            self.focus = None;
            self.render();
        }
    }
    pub fn editing(&self) -> bool {
        self.modal.is_none() && (self.page == Page::Create || self.binding.is_some())
    }
    pub fn text(&mut self, s: &str) {
        if self.editing() {
            for c in s.chars() {
                if c.is_ascii() && !c.is_ascii_control() && self.typed.len() < 20 {
                    self.typed.push(c)
                }
            }
        }
    }
    pub fn backspace(&mut self) {
        if self.editing() {
            self.typed.pop();
        }
    }
    pub fn accept_text(&mut self) {
        if let Some((pad, row, col)) = self.binding.take() {
            if pad {
                self.settings.pad[row] = self.typed.clone()
            } else {
                self.settings.keys[row * 2 + col] = self.typed.clone()
            }
            self.typed.clear();
        } else if self.page == Page::Create {
            self.perform(Action::Create);
        }
    }
    pub fn capture_key(&mut self, label: &str) -> bool {
        if self.binding.is_some() {
            self.typed = label
                .chars()
                .filter(|c| c.is_ascii() && !c.is_ascii_control())
                .take(20)
                .collect();
            self.accept_text();
            true
        } else {
            false
        }
    }
    pub fn activate(&mut self) -> bool {
        let Some(a) = self
            .focus
            .and_then(|i| self.hits.get(i))
            .map(|h| h.action.clone())
        else {
            return false;
        };
        self.perform(a)
    }
    pub fn perform(&mut self, a: Action) -> bool {
        match a {
            Action::Route(p) => self.show(p),
            Action::Back => self.escape(),
            Action::Quit => self.quit_prompt(),
            Action::New => {
                self.time = Some(0.);
                self.focus = None;
            }
            Action::Answer(answer) => {
                match self.modal.take() {
                    Some(0) => {
                        if answer == 0 {
                            self.saved = self.settings.clone();
                            self.save_requested = true;
                        } else if answer == 1 {
                            self.settings = self.saved.clone();
                        }
                        if answer != 2 {
                            self.show(self.destination)
                        }
                    }
                    Some(1) if answer == 0 => {
                        self.settings = self.saved.clone();
                        return true;
                    }
                    Some(2) if answer == 0 => {
                        if let Some(i) = self.selected {
                            self.profiles.remove(i);
                            self.active = self.active.and_then(|a| {
                                if a == i {
                                    None
                                } else {
                                    Some(if a > i { a - 1 } else { a })
                                }
                            });
                            self.selected = (!self.profiles.is_empty()).then_some(0);
                            self.save_requested = true;
                            if self.profiles.is_empty() {
                                self.show(Page::Create)
                            }
                        }
                    }
                    _ => {}
                }
                self.focus = None;
            }
            Action::Default => {
                let d = Settings::default();
                match self.page {
                    Page::Effects | Page::Advanced => {
                        self.settings.values[..9].copy_from_slice(&d.values[..9])
                    }
                    Page::Game => self.settings.values[9..11].copy_from_slice(&d.values[9..11]),
                    Page::Sound => self.settings.values[11..17].copy_from_slice(&d.values[11..17]),
                    Page::Keyboard | Page::Gamepad => {
                        self.settings.values[17..].copy_from_slice(&d.values[17..]);
                        self.settings.keys = d.keys;
                        self.settings.pad = d.pad;
                    }
                    _ => {}
                }
            }
            Action::Choice(i, v) => self.settings.values[i] = v.min(MAX[i]),
            Action::Step(i, d) => self.step(i, d),
            Action::Slider(..) => {}
            Action::Scroll(d) => self.scroll(d),
            Action::Binding(p, r, c) => {
                self.binding = Some((p, r, c));
                self.typed.clear();
            }
            Action::Create => {
                let name = self.typed.trim().to_owned();
                if name.is_empty()
                    || name.len() > 20
                    || self.profiles.len() >= 5
                    || self.profiles.iter().any(|p| p.eq_ignore_ascii_case(&name))
                {
                    self.error =
                        "Use a unique name (1-20 ASCII characters, five profiles maximum).".into()
                } else {
                    self.profiles.push(name);
                    self.active = Some(self.profiles.len() - 1);
                    self.selected = self.active;
                    self.save_requested = true;
                    self.show(Page::Main)
                }
            }
            Action::Profile(i) => self.selected = Some(i),
            Action::Delete => {
                if self.selected.is_some() {
                    self.modal = Some(2);
                    self.focus = None;
                }
            }
            Action::Select => {
                if self.selected.is_some() {
                    self.active = self.selected;
                    self.save_requested = true;
                    self.show(Page::Main)
                }
            }
        }
        self.render();
        false
    }
    fn tint(&self, c: [f32; 3]) -> [f32; 3] {
        if self.srgb {
            c.map(|v| {
                if v <= 0.04045 {
                    v / 12.92
                } else {
                    ((v + 0.055) / 1.055).powf(2.4)
                }
            })
        } else {
            c
        }
    }
    fn sprite(&mut self, name: &str, rect: [f32; 4], color: [f32; 3]) {
        let s = self.sprites[name];
        let c = self.tint(color);
        for (u, v) in [(0., 0.), (1., 0.), (1., 1.), (0., 0.), (1., 1.), (0., 1.)] {
            self.vertices.extend([
                (rect[0] + u * rect[2]) / 400. - 1.,
                (rect[1] + v * rect[3]) / 300. - 1.,
                0.,
                (s.rect[0] + u * s.rect[2]) / s.texture_size[0],
                (s.rect[1] + v * s.rect[3]) / s.texture_size[1],
                c[0],
                c[1],
                c[2],
                s.layer as f32,
            ]);
        }
    }
    fn box_at(&mut self, r: [f32; 4]) {
        self.sprite("panel", r, [1.; 3]);
    }
    #[allow(clippy::too_many_arguments)]
    fn text_at(
        &mut self,
        label: &str,
        x: f32,
        y: f32,
        size: f32,
        align: u8,
        action: Option<Action>,
        selected: bool,
        disabled: bool,
        width: f32,
    ) {
        let font = choose_font(&self.font_sizes, size * 1.25 * self.pixel_scale);
        let mut pen = 0.;
        let mut placements = Vec::new();
        let mut bounds = [f32::MAX, f32::MAX, f32::MIN, f32::MIN];
        for c in label
            .chars()
            .filter(|c| c.is_ascii() && !c.is_ascii_control())
        {
            let key = font.map_or_else(
                || format!("c{}", c as u32),
                |size| format!("f{size}_c{}", c as u32),
            );
            let s = self.sprites[&key];
            if c != ' ' {
                let px = pen + s.metrics[0];
                let py = s.metrics[1];
                bounds[0] = bounds[0].min(px);
                bounds[1] = bounds[1].min(py);
                bounds[2] = bounds[2].max(px + s.rect[2]);
                bounds[3] = bounds[3].max(py + s.rect[3]);
                placements.push((key, px, py, s.rect[2], s.rect[3]));
            }
            pen += s.metrics[2];
        }
        if placements.is_empty() {
            return;
        }
        let scale = size / font.map_or(self.font_size, |v| v as f32) * 1.25;
        let w = (bounds[2] - bounds[0]) * scale;
        let sx = if width > 0. && w > width {
            scale * width / w
        } else {
            scale
        };
        let w = (bounds[2] - bounds[0]) * sx;
        let h = (bounds[3] - bounds[1]) * scale;
        let x = x - if align == 1 {
            w / 2.
        } else if align == 2 {
            w
        } else {
            0.
        };
        let highlighted = selected
            || action.as_ref().is_some_and(|a| {
                self.focus
                    .and_then(|i| self.hits.get(i))
                    .is_some_and(|h| &h.action == a)
            });
        // Focus is indexed by construction order, independent of changing text width.
        let highlighted = highlighted || action.is_some() && self.focus == Some(self.hits.len());
        let color = if disabled {
            [0.4; 3]
        } else if highlighted {
            [1.; 3]
        } else {
            [188. / 255., 160. / 255., 122. / 255.]
        };
        for (key, px, py, pw, ph) in placements {
            self.sprite(
                &key,
                [
                    x + (px - bounds[0]) * sx,
                    y + (py - bounds[1]) * scale,
                    pw * sx,
                    ph * scale,
                ],
                color,
            )
        }
        if let Some(action) = action.filter(|_| !disabled) {
            self.hits.push(Hit {
                action,
                rect: [x - 5., y - 5., x + w + 5., y + h.max(22.)],
            })
        }
    }
    fn label(&mut self, s: &str, x: f32, y: f32, size: f32) {
        self.text_at(s, x, y, size, 0, None, false, false, 0.)
    }
    fn button(&mut self, s: &str, x: f32, y: f32, a: Action) {
        self.text_at(s, x, y, 18., 0, Some(a), false, false, 0.)
    }
    fn choices(
        &mut self,
        s: &str,
        y: f32,
        i: usize,
        values: &[&str],
        positions: &[f32],
        enabled: bool,
    ) {
        self.label(s, 187., y, 14.);
        for (v, (label, x)) in values.iter().zip(positions).enumerate() {
            self.text_at(
                label,
                *x,
                y,
                12.,
                1,
                Some(Action::Choice(i, v)),
                self.settings.values[i] == v,
                !enabled,
                0.,
            )
        }
    }
    #[allow(clippy::too_many_arguments)] // Screenshot layout coordinates and setting identity.
    fn slider(
        &mut self,
        s: &str,
        y: f32,
        i: usize,
        value: &str,
        start: f32,
        end: f32,
        enabled: bool,
    ) {
        self.label(s, 187., y - 15., 14.);
        self.label(value, 187., y + 9., 12.);
        let color = if enabled { [1.; 3] } else { [0.45; 3] };
        let h = self.sprites["bar"].rect[3];
        self.sprite("bar", [start, y - h / 2., end - start, h], color);
        for (name, x, d) in [("minus", start - 36., -1), ("plus", end, 1)] {
            let r = self.sprites[name].rect;
            self.sprite(name, [x, y - r[3] / 2., r[2], r[3]], color);
            if enabled {
                self.hits.push(Hit {
                    action: Action::Step(i, d),
                    rect: [x, y - 22., x + r[2], y + 22.],
                })
            }
        }
        let r = self.sprites["handle"].rect;
        let x = start + self.settings.values[i] as f32 / MAX[i] as f32 * (end - start);
        self.sprite("handle", [x - r[2] / 2., y - r[3] / 2., r[2], r[3]], color);
        if enabled {
            self.hits.push(Hit {
                action: Action::Slider(i, start, end),
                rect: [start, y - 24., end, y + 24.],
            })
        }
    }
    pub fn render(&mut self) {
        self.vertices.clear();
        self.hits.clear();
        if self.time.is_some() {
            return;
        }
        if let Some(modal) = self.modal {
            self.box_at([100., 205., 590., 190.]);
            let lines = match modal {
                0 => [
                    "Game options have been modified.",
                    "Would you like to keep these changes?",
                ],
                1 => ["Do you really want to quit", "the OpenJade preview?"],
                _ => ["Delete this OpenJade profile?", ""],
            };
            for (i, s) in lines.iter().enumerate() {
                self.text_at(
                    s,
                    400.,
                    238. + i as f32 * 42.,
                    18.,
                    1,
                    None,
                    false,
                    false,
                    570.,
                )
            }
            for (i, (s, x)) in if modal == 0 {
                vec![("Yes", 255.), ("No", 400.), ("Cancel", 535.)]
            } else {
                vec![("Yes", 255.), ("No", 540.)]
            }
            .into_iter()
            .enumerate()
            {
                self.text_at(
                    s,
                    x,
                    350.,
                    18.,
                    1,
                    Some(Action::Answer(i as u8)),
                    false,
                    false,
                    0.,
                )
            }
        } else {
            let title = match self.page {
                Page::Create => "Create a new profile:",
                Page::Profiles => "Choose your profile",
                Page::Options => "Options",
                Page::Keyboard => "Controls - Keyboard",
                Page::Gamepad => "Controls - Gamepad",
                Page::Game => "Game Options",
                Page::Effects | Page::Advanced => "Graphics",
                Page::Sound => "Sound",
                Page::Credits => "Credits",
                _ => "",
            };
            self.label(
                title,
                31.,
                20.,
                if matches!(self.page, Page::Create | Page::Profiles) {
                    21.
                } else {
                    28.
                },
            );
            match self.page {
                Page::Main => {
                    self.sprite("logo", [20., 20., 480., 120.], [1.; 3]);
                    for (s, y, a) in [
                        ("Start New Game", 162., Action::New),
                        ("Options", 287., Action::Route(Page::Options)),
                        ("Credits", 350., Action::Route(Page::Credits)),
                        ("Quit", 412., Action::Quit),
                    ] {
                        self.button(s, 375., y, a)
                    }
                    self.text_at("Load Saved Game", 375., 225., 18., 0, None, false, true, 0.);
                    self.button("Change Profile", 62., 536., Action::Route(Page::Profiles));
                }
                Page::Options => {
                    for (s, y, p) in [
                        ("Controls", 170., Page::Keyboard),
                        ("Game", 232., Page::Game),
                        ("Graphics", 295., Page::Effects),
                        ("Sound", 357., Page::Sound),
                    ] {
                        self.button(s, 375., y, Action::Route(p))
                    }
                }
                Page::Effects | Page::Advanced => {
                    self.box_at([155., 95., 590., 180.]);
                    self.box_at([
                        148.,
                        296.,
                        598.,
                        if self.page == Page::Effects {
                            220.
                        } else {
                            170.
                        },
                    ]);
                    let (w, h) = self.resolution();
                    self.slider(
                        "Window Resolution",
                        155.,
                        0,
                        &format!("{w}x{h}"),
                        427.,
                        691.,
                        true,
                    );
                    self.slider(
                        "Gamma",
                        217.,
                        1,
                        &format!("{:.2}", self.gamma() as f32 / 100.),
                        427.,
                        691.,
                        true,
                    );
                    self.text_at(
                        "Effects",
                        31.,
                        323.,
                        14.,
                        0,
                        Some(Action::Route(Page::Effects)),
                        self.page == Page::Effects,
                        false,
                        0.,
                    );
                    self.text_at(
                        "Advanced",
                        31.,
                        354.,
                        14.,
                        0,
                        Some(Action::Route(Page::Advanced)),
                        self.page == Page::Advanced,
                        false,
                        0.,
                    );
                    if self.page == Page::Effects {
                        self.choices(
                            "Special Effects",
                            323.,
                            5,
                            &["High", "Medium", "Low"],
                            &[415., 540., 664.],
                            false,
                        );
                        self.choices(
                            "Shadow Effects",
                            373.,
                            6,
                            &["High", "Medium", "None"],
                            &[415., 540., 664.],
                            false,
                        );
                        self.choices(
                            "Water Effects",
                            423.,
                            7,
                            &["On", "Off"],
                            &[415., 540.],
                            false,
                        );
                        self.choices("Fog", 473., 8, &["On", "Off"], &[415., 540.], false);
                    } else {
                        self.choices(
                            "Filtering",
                            323.,
                            2,
                            &["Trilinear", "Bilinear", "None"],
                            &[415., 540., 664.],
                            true,
                        );
                        self.choices(
                            "V-Sync.",
                            373.,
                            3,
                            &["Disable", "Enable"],
                            &[415., 540.],
                            true,
                        );
                        self.choices(
                            "Texture Quality",
                            423.,
                            4,
                            &["High", "Low"],
                            &[415., 540.],
                            false,
                        );
                    }
                    self.label(
                        "Grey options: rendering behavior not implemented.",
                        187.,
                        515.,
                        10.,
                    );
                }
                Page::Game => {
                    self.box_at([150., 190., 645., 154.]);
                    let v = ["None", "Few", "Normal", "Many"][self.settings.values[9]];
                    self.slider("Frequency of hints", 245., 9, v, 477., 742., false);
                    self.choices("Tutorials", 291., 10, &["Yes", "No"], &[563., 688.], false);
                    self.label("Gameplay systems are not implemented.", 187., 365., 12.);
                }
                Page::Sound => {
                    self.box_at([155., 64., 615., 250.]);
                    self.box_at([160., 321., 610., 180.]);
                    for (i, s) in ["Music Volume", "Voice Volume", "Sound FX Volume"]
                        .iter()
                        .enumerate()
                    {
                        self.slider(
                            s,
                            117. + i as f32 * 63.,
                            11 + i,
                            &format!("{}%", self.settings.values[11 + i]),
                            451.,
                            716.,
                            false,
                        )
                    }
                    self.choices(
                        "Audio Virtualization",
                        367.,
                        14,
                        &["None", "Partial", "Full"],
                        &[474., 576., 677.],
                        false,
                    );
                    self.choices(
                        "3D Accelerator",
                        405.,
                        15,
                        &["Yes", "No"],
                        &[563., 688.],
                        false,
                    );
                    self.sprite("eax", [187., 431., 104., 33.], [0.5; 3]);
                    self.choices("", 445., 16, &["Yes", "No"], &[563., 688.], false);
                    self.label("Audio playback is not implemented.", 187., 510., 12.);
                }
                Page::Keyboard | Page::Gamepad => {
                    let pad = self.page == Page::Gamepad;
                    self.text_at(
                        "Gamepad",
                        31.,
                        72.,
                        14.,
                        0,
                        Some(Action::Route(Page::Gamepad)),
                        pad,
                        false,
                        0.,
                    );
                    self.text_at(
                        "Keyboard",
                        31.,
                        104.,
                        14.,
                        0,
                        Some(Action::Route(Page::Keyboard)),
                        !pad,
                        false,
                        0.,
                    );
                    self.box_at([180., 63., 205., 252.]);
                    self.box_at([413., 63., 173., 252.]);
                    if !pad {
                        self.box_at([605., 63., 175., 252.]);
                    }
                    for row in 0..6 {
                        let i = self.offset + row;
                        let y = 97. + row as f32 * 31.;
                        self.text_at(ACTIONS[i], 283., y, 13., 1, None, false, false, 192.);
                        for (col, x) in if pad { vec![500.] } else { vec![500., 695.] }
                            .into_iter()
                            .enumerate()
                        {
                            self.sprite("field", [x - 61., y - 3., 122., 22.], [1.; 3]);
                            let editing = self.binding == Some((pad, i, col));
                            let label = if editing {
                                "Press a key...".to_owned()
                            } else if pad {
                                self.settings.pad[i].clone()
                            } else {
                                self.settings.keys[i * 2 + col].clone()
                            };
                            self.text_at(&label, x, y, 12., 1, None, editing, false, 114.);
                            if !pad {
                                self.hits.push(Hit {
                                    action: Action::Binding(pad, i, col),
                                    rect: [x - 61., y - 3., x + 61., y + 23.],
                                })
                            }
                        }
                    }
                    for (name, y, d, enabled) in [
                        ("up", 66., -5, self.offset > 0),
                        ("down", 282., 5, self.offset < 12),
                    ] {
                        self.sprite(
                            name,
                            [272., y, 16., 22.],
                            if enabled { [1.; 3] } else { [0.3; 3] },
                        );
                        if enabled {
                            self.hits.push(Hit {
                                action: Action::Scroll(d),
                                rect: [267., y - 4., 299., y + 26.],
                            })
                        }
                    }
                    self.box_at([165., 320., 625., 177.]);
                    self.slider(
                        "Mouse Speed",
                        363.,
                        17,
                        &format!("{}%", self.settings.values[17]),
                        477.,
                        742.,
                        false,
                    );
                    self.choices(
                        "Camera Freelook",
                        411.,
                        18,
                        &["Normal", "Inverted"],
                        &[470., 626.],
                        false,
                    );
                    self.choices(
                        "Camera Navigation",
                        462.,
                        19,
                        &["Normal", "Inverted"],
                        &[470., 626.],
                        false,
                    );
                    self.label(
                        if pad {
                            "Gamepad input is not integrated."
                        } else {
                            "Bindings stored only. No gameplay. Esc cancels capture."
                        },
                        187.,
                        510.,
                        10.,
                    );
                }
                Page::Create => {
                    self.box_at([175., 241., 450., 84.]);
                    self.label(&format!("{}_", self.typed), 216., 281., 20.);
                    self.button(
                        if self.profiles.is_empty() {
                            "Quit"
                        } else {
                            "Back"
                        },
                        62.,
                        536.,
                        if self.profiles.is_empty() {
                            Action::Quit
                        } else {
                            Action::Route(Page::Profiles)
                        },
                    );
                    self.text_at(
                        "Create",
                        720.,
                        536.,
                        18.,
                        2,
                        Some(Action::Create),
                        false,
                        false,
                        0.,
                    );
                }
                Page::Profiles => {
                    self.box_at([84., 134., 330., 245.]);
                    for (i, name) in self.profiles.clone().iter().enumerate() {
                        self.text_at(
                            name,
                            250.,
                            186. + i as f32 * 33.,
                            18.,
                            1,
                            Some(Action::Profile(i)),
                            self.selected == Some(i),
                            false,
                            295.,
                        )
                    }
                    self.text_at(
                        "New Profile",
                        250.,
                        444.,
                        18.,
                        1,
                        Some(Action::Route(Page::Create)),
                        false,
                        self.profiles.len() >= 5,
                        0.,
                    );
                    self.button("Quit", 62., 536., Action::Quit);
                    self.text_at(
                        "Delete",
                        312.,
                        536.,
                        18.,
                        0,
                        Some(Action::Delete),
                        false,
                        self.selected.is_none(),
                        0.,
                    );
                    self.text_at(
                        "Select",
                        550.,
                        536.,
                        18.,
                        0,
                        Some(Action::Select),
                        false,
                        self.selected.is_none(),
                        0.,
                    );
                }
                Page::Credits => {
                    self.text_at(
                        "OpenJade - independent research preview",
                        400.,
                        260.,
                        18.,
                        1,
                        None,
                        false,
                        false,
                        700.,
                    );
                    self.text_at(
                        "Original game credits are not integrated.",
                        400.,
                        305.,
                        16.,
                        1,
                        None,
                        false,
                        false,
                        700.,
                    );
                }
            }
            if !matches!(self.page, Page::Main | Page::Create | Page::Profiles) {
                self.button("Back", 62., 536., Action::Back)
            }
            if matches!(
                self.page,
                Page::Effects
                    | Page::Advanced
                    | Page::Keyboard
                    | Page::Gamepad
                    | Page::Game
                    | Page::Sound
            ) {
                self.text_at(
                    "Default Settings",
                    748.,
                    536.,
                    18.,
                    2,
                    Some(Action::Default),
                    false,
                    false,
                    0.,
                )
            }
        }
        if !self.error.is_empty() {
            self.text_at(
                &self.error.clone(),
                400.,
                575.,
                11.,
                1,
                None,
                false,
                false,
                780.,
            );
        }
        if let Some((x, y)) = self.pointer {
            self.sprite("cursor", [x, y, 40., 40.], [1.; 3]);
        }
        if self.focus.is_some_and(|i| i >= self.hits.len()) {
            self.focus = None;
        }
    }
    pub fn state_text(&self) -> String {
        let mut lines = vec![
            "OJMNU001".to_owned(),
            self.saved
                .values
                .iter()
                .map(usize::to_string)
                .collect::<Vec<_>>()
                .join(" "),
            self.profiles.len().to_string(),
            self.active.map_or("-".into(), |i| i.to_string()),
        ];
        lines.extend(self.profiles.clone());
        lines.extend(self.saved.keys.clone());
        lines.extend(self.saved.pad.clone());
        lines.join("\n") + "\n"
    }
    pub fn restore(&mut self, text: &str) -> io::Result<()> {
        if text.len() > 8192 || !text.is_ascii() {
            return Err(bad());
        }
        let mut lines = text.lines();
        if lines.next() != Some("OJMNU001") {
            return Err(bad());
        }
        let vals = lines
            .next()
            .ok_or_else(bad)?
            .split_whitespace()
            .map(str::parse::<usize>)
            .collect::<Result<Vec<_>, _>>()
            .map_err(|_| bad())?;
        if vals.len() != 20 || vals.iter().zip(MAX).any(|(v, m)| *v > m) {
            return Err(bad());
        }
        let n = lines
            .next()
            .ok_or_else(bad)?
            .parse::<usize>()
            .map_err(|_| bad())?;
        if n > 5 {
            return Err(bad());
        }
        let active = match lines.next() {
            Some("-") => None,
            Some(s) => Some(s.parse::<usize>().map_err(|_| bad())?),
            None => return Err(bad()),
        };
        if active.is_some_and(|i| i >= n) {
            return Err(bad());
        }
        let mut profiles: Vec<String> = vec![];
        for _ in 0..n {
            let s = lines.next().ok_or_else(bad)?;
            if s.is_empty()
                || s.len() > 20
                || s.trim() != s
                || s.chars().any(|c| c.is_ascii_control())
                || profiles.iter().any(|p| p.eq_ignore_ascii_case(s))
            {
                return Err(bad());
            }
            profiles.push(s.to_owned());
        }
        let mut bindings = Vec::new();
        for _ in 0..54 {
            let s = lines.next().ok_or_else(bad)?;
            if s.len() > 20 || s.chars().any(|c| c.is_ascii_control()) {
                return Err(bad());
            }
            bindings.push(s.to_owned());
        }
        if lines.next().is_some() {
            return Err(bad());
        }
        self.settings = Settings {
            values: vals.try_into().unwrap(),
            keys: bindings[..36].to_vec(),
            pad: bindings[36..].to_vec(),
        };
        self.saved = self.settings.clone();
        self.profiles = profiles;
        self.active = active;
        self.selected = active.or((n > 0).then_some(0));
        self.show(if active.is_some() {
            Page::Main
        } else if n > 0 {
            Page::Profiles
        } else {
            Page::Create
        });
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (Vec<u8>, Scene) {
        let camera = [0., 0., 0., 1., 0., 0., 0., 1., 0., 0., 0., 1., 59.37908];
        let scene = Scene {
            color_pipeline: ColorPipeline::Srgb,
            texture_sizes: vec![[512, 512]],
            ui_start: 1,
            filter: TextureFilter::Linear,
            vertices: vec![],
            width: 512,
            height: 512,
            layers: 1,
            pixels: vec![],
            camera,
            draws: vec![],
        };
        let names: Vec<_> = [
            "panel", "logo", "cursor", "eax", "field", "up", "down", "bar", "minus", "plus",
            "handle",
        ]
        .into_iter()
        .map(str::to_owned)
        .chain((32..127).map(|i| format!("c{i}")))
        .collect();
        let mut b = b"OJUI0002".to_vec();
        b.extend(1u32.to_le_bytes());
        b.extend(18f32.to_le_bytes());
        b.extend((names.len() as u32).to_le_bytes());
        for n in names {
            b.extend((n.len() as u32).to_le_bytes());
            b.extend(n.as_bytes());
            for v in [0u32, 0, 0, 1, 1] {
                b.extend(v.to_le_bytes())
            }
            for v in [0f32, 0., 1.] {
                b.extend(v.to_le_bytes())
            }
        }
        b.resize(b.len() + 512 * 512 * 4, 255);
        b.extend(541u32.to_le_bytes());
        for _ in 0..541 {
            for c in camera {
                b.extend(c.to_le_bytes())
            }
        }
        (b, scene)
    }
    #[test]
    fn version_three_preserves_wide_texture_rows_and_rejects_bad_dimensions() {
        let (old, mut scene) = fixture();
        scene.pixels.resize(512 * 512 * 4, 0);
        let mut r = Reader(&old[8..]);
        let _ = r.word().unwrap();
        let font = r.float().unwrap();
        let count = r.word().unwrap();
        let mut b = b"OJUI0003".to_vec();
        b.extend(2u32.to_le_bytes());
        b.extend(font.to_le_bytes());
        b.extend(count.to_le_bytes());
        for v in [512u32, 512, 1024, 256, 1, 36] {
            b.extend(v.to_le_bytes());
        }
        for _ in 0..count {
            let n = r.word().unwrap() as usize;
            let name = std::str::from_utf8(r.take(n).unwrap()).unwrap();
            let new = if name.starts_with('c') && name[1..].parse::<u32>().is_ok() {
                format!("f36_{name}")
            } else {
                name.to_owned()
            };
            b.extend((new.len() as u32).to_le_bytes());
            b.extend(new.as_bytes());
            let mut values = [0u32; 5];
            for v in &mut values {
                *v = r.word().unwrap();
            }
            if name == "logo" {
                values = [1, 0, 0, 1024, 256];
            }
            for v in values {
                b.extend(v.to_le_bytes());
            }
            b.extend(r.take(12).unwrap());
        }
        b.extend(r.take(512 * 512 * 4).unwrap());
        let wide: Vec<u8> = (0..1024 * 256 * 4)
            .map(|i| ((i / 4096) % 256) as u8)
            .collect();
        b.extend(&wide);
        b.extend(r.0);
        let menu = NativeMenu::decode(&b, &mut scene).unwrap();
        assert_eq!(menu.font_sizes, vec![36]);
        assert_eq!(scene.texture_sizes[2], [1024, 256]);
        assert_eq!(scene.texture_pixels(2), wide);
        let (_, mut fresh) = fixture();
        b[28..32].copy_from_slice(&2048u32.to_le_bytes());
        b[32..36].copy_from_slice(&2048u32.to_le_bytes());
        assert!(NativeMenu::decode(&b, &mut fresh).is_err());
        assert_eq!(fresh.layers, 1);
    }
    #[test]
    fn renderer_receives_changes_only_after_back_and_yes() {
        let mut m = menu();
        let baseline = m.applied_display();
        let disk = m.state_text();
        m.perform(Action::Route(Page::Advanced));
        for (i, v) in [(0, 2), (1, 67), (2, 0), (3, 0)] {
            m.perform(Action::Choice(i, v));
        }
        assert_eq!(m.gamma(), 67);
        assert_eq!(m.resolution(), (1024, 768));
        assert_eq!(m.applied_display(), baseline);
        assert_eq!(m.state_text(), disk);
        m.escape();
        assert_eq!(m.modal, Some(0));
        assert_eq!(m.applied_display(), baseline);
        m.perform(Action::Answer(2));
        assert_eq!(m.page, Page::Advanced);
        assert_eq!(m.gamma(), 67);
        assert_eq!(m.applied_display(), baseline);
        m.escape();
        m.perform(Action::Answer(1));
        assert_eq!(m.settings, m.saved);
        assert_eq!(m.applied_display(), baseline);
        assert!(!m.save_requested);
        m.perform(Action::Route(Page::Advanced));
        for (i, v) in [(0, 2), (1, 67), (2, 0), (3, 0)] {
            m.perform(Action::Choice(i, v));
        }
        m.escape();
        m.perform(Action::Answer(0));
        let applied = m.applied_display();
        assert_eq!(applied.gamma, 67);
        assert_eq!(applied.resolution, (1024, 768));
        assert_eq!(applied.filter, TextureFilter::Trilinear);
        assert!(!applied.vsync);
        assert!(m.save_requested);
        let mut restored = menu();
        restored.restore(&m.state_text()).unwrap();
        assert_eq!(restored.applied_display(), applied);
        m.perform(Action::Route(Page::Advanced));
        m.perform(Action::Default);
        assert_eq!(m.gamma(), 0);
        assert_eq!(m.applied_display(), applied);
        m.escape();
        m.perform(Action::Answer(0));
        assert_eq!(m.applied_display().gamma, 0);
        assert_eq!(m.applied_display().resolution, (800, 600));
    }
    fn menu() -> NativeMenu {
        let (b, mut s) = fixture();
        NativeMenu::decode(&b, &mut s).unwrap()
    }
    #[test]
    fn bundle_validation_is_transactional() {
        let (b, mut s) = fixture();
        for bytes in [
            &b[..8],
            &b[..b.len() - 1],
            &[b.as_slice(), b"extra"].concat(),
        ] {
            assert!(NativeMenu::decode(bytes, &mut s).is_err());
            assert_eq!(s.layers, 1);
            assert!(s.pixels.is_empty())
        }
        let m = NativeMenu::decode(&b, &mut s).unwrap();
        assert_eq!(s.layers, 2);
        assert_eq!(m.cameras.len(), 541);
    }
    #[test]
    fn preview_cancel_discard_save_and_defaults() {
        let mut m = menu();
        m.perform(Action::Route(Page::Advanced));
        m.perform(Action::Choice(1, 72));
        m.perform(Action::Choice(2, 0));
        m.escape();
        assert_eq!(m.modal, Some(0));
        m.perform(Action::Answer(2));
        assert_eq!(m.gamma(), 72);
        assert_eq!(m.page, Page::Advanced);
        m.escape();
        m.perform(Action::Answer(1));
        assert_eq!(m.gamma(), 0);
        assert_eq!(m.filter(), TextureFilter::Linear);
        m.perform(Action::Route(Page::Advanced));
        m.perform(Action::Choice(1, 42));
        m.escape();
        m.perform(Action::Answer(0));
        assert_eq!(m.saved.values[1], 42);
        m.perform(Action::Route(Page::Advanced));
        m.perform(Action::Default);
        assert_eq!(m.gamma(), 0);
        m.escape();
        m.perform(Action::Answer(1));
        assert_eq!(m.gamma(), 42);
    }
    #[test]
    fn profiles_bindings_and_state_round_trip() {
        let mut m = menu();
        m.text("Prince");
        m.accept_text();
        assert_eq!(m.page, Page::Main);
        assert_eq!(m.active, Some(0));
        m.perform(Action::Route(Page::Create));
        m.text("prince");
        m.accept_text();
        assert_eq!(m.profiles.len(), 1);
        assert!(!m.error.is_empty());
        m.perform(Action::Route(Page::Keyboard));
        m.perform(Action::Binding(false, 0, 0));
        assert!(m.capture_key("W"));
        m.escape();
        m.perform(Action::Answer(0));
        let saved = m.state_text();
        let mut reloaded = menu();
        reloaded.restore(&saved).unwrap();
        assert_eq!(reloaded.profiles, vec!["Prince"]);
        assert_eq!(reloaded.settings.keys[0], "W");
        assert_eq!(reloaded.page, Page::Main);
        let old = reloaded.state_text();
        assert!(reloaded
            .restore(&saved.replace("OJMNU001", "not ours"))
            .is_err());
        assert_eq!(old, reloaded.state_text());
        m.perform(Action::Route(Page::Profiles));
        m.perform(Action::Delete);
        m.perform(Action::Answer(0));
        assert!(m.profiles.is_empty());
        assert_eq!(m.page, Page::Create);
    }
    #[test]
    fn scrolling_dragging_and_camera_reset() {
        let mut m = menu();
        m.perform(Action::Route(Page::Keyboard));
        m.scroll(100);
        assert_eq!(m.offset, 12);
        m.scroll(-100);
        assert_eq!(m.offset, 0);
        m.perform(Action::Route(Page::Advanced));
        let i = m
            .hits
            .iter()
            .position(|h| matches!(h.action, Action::Slider(1, _, _)))
            .unwrap();
        m.focus = Some(i);
        m.pointer = Some((500., 217.));
        m.press();
        m.motion(900., 217.);
        assert_eq!(m.gamma(), 100);
        m.motion(-20., 217.);
        assert_eq!(m.gamma(), 0);
        m.release();
        m.perform(Action::New);
        m.tick(20.);
        assert_eq!(m.time, Some(9.));
        m.render();
        assert!(m.vertices.is_empty());
        m.escape();
        assert_eq!(m.time, None);
        assert_eq!(m.page, Page::Main);
    }
    #[test]
    fn all_pages_have_bounded_geometry_and_honest_controls() {
        let mut m = menu();
        for p in [
            Page::Create,
            Page::Profiles,
            Page::Main,
            Page::Options,
            Page::Keyboard,
            Page::Gamepad,
            Page::Game,
            Page::Effects,
            Page::Advanced,
            Page::Sound,
            Page::Credits,
        ] {
            m.perform(Action::Route(p));
            assert!(!m.vertices.is_empty());
            assert!(m.vertices.len() < 65536 * 9);
            assert!(m.vertices.iter().all(|v| v.is_finite()));
            if matches!(p, Page::Sound | Page::Game | Page::Effects) {
                assert!(!m
                    .hits
                    .iter()
                    .any(|h| matches!(h.action,Action::Choice(i,_) if i>=4)));
            }
        }
    }
    #[test]
    fn malformed_state_does_not_change_settings() {
        let mut m = menu();
        let original = m.state_text();
        for text in [
            original.replacen("1 0 1", "1 999 1", 1),
            format!("{original}trailing\n"),
            "x".repeat(9000),
        ] {
            assert!(m.restore(&text).is_err());
            assert_eq!(m.state_text(), original);
        }
    }
}

/// Select the smallest available raster size that avoids magnification, capped at the largest.
fn choose_font(sizes: &[u32], pixels: f32) -> Option<u32> {
    sizes
        .iter()
        .copied()
        .find(|s| *s as f32 >= pixels)
        .or_else(|| sizes.last().copied())
}
#[cfg(test)]
mod scale_tests {
    use super::*;
    #[test]
    fn font_tracks_actual_viewport_pixels() {
        let sizes = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48];
        assert_eq!(choose_font(&sizes, 18. * 1.25), Some(24));
        assert_eq!(choose_font(&sizes, 18. * 1.25 * 2.), Some(48));
        assert_eq!(choose_font(&sizes, 100.), Some(48));
        assert_eq!(choose_font(&[], 20.), None);
    }
}
