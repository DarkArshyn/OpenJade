use jade_assets::native_ui::NativeMenu;
use jade_assets::ui::{viewport, Menu};
use jade_render_vulkan::window::{validation_errors, Presenter};
use std::{sync::Arc, time::Instant};
use winit::{
    application::ApplicationHandler,
    dpi::PhysicalSize,
    event::WindowEvent,
    event_loop::{ActiveEventLoop, EventLoop},
    window::WindowId,
};
use winit::{
    event::{ElementState, MouseButton},
    keyboard::{Key, NamedKey},
};

#[derive(Default)]
struct App {
    presenter: Option<Presenter>,
    validation: bool,
    smoke: bool,
    frames: u32,
    failed: bool,
    scene: Option<jade_assets::Scene>,
    menu: Option<Menu>,
    native_menu: Option<NativeMenu>,
    native_state: Option<std::path::PathBuf>,
    native_resolution: Option<(u32, u32)>,
    modifiers: winit::keyboard::ModifiersState,
    last_frame: Option<Instant>,
    pointer: Option<(f32, f32)>,
    settings_path: Option<std::path::PathBuf>,
    settings_poll: Option<Instant>,
    gamma: Option<u8>,
    settings_error: bool,
}
impl ApplicationHandler for App {
    fn resumed(&mut self, event_loop: &ActiveEventLoop) {
        if self.presenter.is_some() {
            return;
        }
        let result = (|| {
            let window = Arc::new(
                event_loop.create_window(
                    winit::window::Window::default_attributes()
                        .with_title(if self.scene.is_some() {
                            "OpenJade - decoded menu geometry"
                        } else {
                            "OpenJade - Vulkan textured panel"
                        })
                        .with_inner_size(PhysicalSize::new(800, 600)),
                )?,
            );
            Presenter::new(window, self.validation, self.scene.take())
        })();
        match result {
            Ok(p) => {
                p.window.request_redraw();
                self.presenter = Some(p);
            }
            Err(e) => {
                eprintln!("Initialization: {e}");
                self.failed = true;
                event_loop.exit();
            }
        }
    }
    fn window_event(&mut self, event_loop: &ActiveEventLoop, id: WindowId, event: WindowEvent) {
        let Some(p) = self.presenter.as_mut() else {
            return;
        };
        if p.window.id() != id {
            return;
        }
        match event {
            WindowEvent::CloseRequested => {
                if let Some(menu) = &mut self.native_menu {
                    menu.quit_prompt();
                    return;
                }
                if let Some(menu) = &mut self.menu {
                    menu.quit_prompt();
                } else {
                    event_loop.exit();
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
                if let Some(menu) = &mut self.native_menu {
                    let size = p.window.inner_size();
                    let [x, y, w, h] = viewport(size.width, size.height);
                    if w > 0. && h > 0. {
                        let point = (
                            (position.x as f32 - x) * 800. / w,
                            (position.y as f32 - y) * 600. / h,
                        );
                        if (0. ..800.).contains(&point.0) && (0. ..600.).contains(&point.1) {
                            menu.motion(point.0, point.1);
                            p.window.set_cursor_visible(false);
                        } else {
                            menu.unfocus();
                            p.window.set_cursor_visible(true);
                        }
                    }
                    return;
                }
                if let Some(menu) = &mut self.menu {
                    let size = p.window.inner_size();
                    let [x, y, w, h] = viewport(size.width, size.height);
                    if w > 0. && h > 0. {
                        let point = (
                            (position.x as f32 - x) * 800. / w,
                            (position.y as f32 - y) * 600. / h,
                        );
                        self.pointer = Some(point);
                        menu.focus = menu.hit(point.0, point.1);
                    }
                }
            }
            WindowEvent::CursorLeft { .. } | WindowEvent::Focused(false) => {
                if let Some(menu) = &mut self.native_menu {
                    menu.unfocus();
                    p.window.set_cursor_visible(true);
                }
                self.pointer = None;
                if let Some(menu) = &mut self.menu {
                    menu.pressed = None;
                    menu.focus = None;
                }
            }
            WindowEvent::MouseInput {
                state,
                button: MouseButton::Left,
                ..
            } => {
                if let Some(menu) = &mut self.native_menu {
                    if state == ElementState::Pressed {
                        if !menu.capture_key("Mouse 1") {
                            menu.press();
                        }
                    } else if menu.release() {
                        event_loop.exit();
                    }
                    return;
                }
                if let Some(menu) = &mut self.menu {
                    let hit = self.pointer.and_then(|(x, y)| menu.hit(x, y));
                    if state == ElementState::Pressed {
                        menu.pressed = hit;
                    } else {
                        let pressed = menu.pressed.take();
                        if hit.is_some() && hit == pressed {
                            menu.focus = hit;
                            if menu.activate() {
                                event_loop.exit();
                            }
                        }
                    }
                }
            }
            WindowEvent::ModifiersChanged(modifiers) => self.modifiers = modifiers.state(),
            WindowEvent::KeyboardInput { event, .. }
                if event.state == ElementState::Pressed && !event.repeat =>
            {
                if let Some(menu) = &mut self.native_menu {
                    if event.logical_key == Key::Named(NamedKey::Escape) {
                        menu.escape();
                        return;
                    }
                    let key_label = match &event.logical_key {
                        Key::Character(c) => c.to_uppercase(),
                        Key::Named(k) => format!("{k:?}"),
                        _ => String::new(),
                    };
                    if !key_label.is_empty() && menu.capture_key(&key_label) {
                        return;
                    }
                    if menu.editing() {
                        if self.modifiers.control_key()
                            || self.modifiers.alt_key()
                            || self.modifiers.super_key()
                        {
                            return;
                        }
                        match &event.logical_key {
                            Key::Named(NamedKey::Enter) => menu.accept_text(),
                            Key::Named(NamedKey::Backspace) => menu.backspace(),
                            Key::Named(NamedKey::Tab) => menu.navigate(1),
                            Key::Character(c) => menu.text(c),
                            Key::Named(NamedKey::Space) => menu.text(" "),
                            _ => {}
                        }
                    } else {
                        match event.logical_key {
                            Key::Named(NamedKey::ArrowUp) => menu.navigate(-1),
                            Key::Named(NamedKey::ArrowDown) | Key::Named(NamedKey::Tab) => {
                                menu.navigate(1)
                            }
                            Key::Named(NamedKey::ArrowLeft) => menu.adjust(-1),
                            Key::Named(NamedKey::ArrowRight) => menu.adjust(1),
                            Key::Named(NamedKey::Enter) | Key::Named(NamedKey::Space)
                                if menu.activate() =>
                            {
                                event_loop.exit();
                            }
                            _ => {}
                        }
                    }
                    return;
                }
                if let Some(menu) = &mut self.menu {
                    match event.logical_key {
                        Key::Named(NamedKey::ArrowUp) => menu.navigate(-1),
                        Key::Named(NamedKey::ArrowDown) | Key::Named(NamedKey::Tab) => {
                            menu.navigate(1)
                        }
                        Key::Named(NamedKey::Enter) | Key::Named(NamedKey::Space) => {
                            if menu.activate() {
                                event_loop.exit();
                            }
                        }
                        Key::Named(NamedKey::Escape) => menu.escape(),
                        _ => {}
                    }
                }
            }
            WindowEvent::MouseInput {
                state: ElementState::Pressed,
                button,
                ..
            } => {
                if let Some(menu) = &mut self.native_menu {
                    menu.capture_key(match button {
                        MouseButton::Right => "Mouse 2",
                        MouseButton::Middle => "Mouse 3",
                        _ => "Mouse extra",
                    });
                }
            }
            WindowEvent::MouseWheel { delta, .. } => {
                if let Some(menu) = &mut self.native_menu {
                    let y = match delta {
                        winit::event::MouseScrollDelta::LineDelta(_, y) => y,
                        winit::event::MouseScrollDelta::PixelDelta(p) => p.y as f32,
                    };
                    menu.scroll(if y > 0. { -1 } else { 1 });
                }
            }
            WindowEvent::Resized(_) => {
                p.resize();
                p.window.request_redraw();
            }
            WindowEvent::RedrawRequested => {
                let now = Instant::now();
                if self
                    .settings_poll
                    .is_none_or(|last| now.duration_since(last).as_millis() >= 100)
                {
                    self.settings_poll = Some(now);
                    if let Some(path) = &self.settings_path {
                        match jade_assets::settings::GraphicsSettings::load(path) {
                            Ok(settings) => {
                                if self.gamma != Some(settings.preview) {
                                    println!(
                                        "Gamma preview: {} (saved {})",
                                        settings.preview, settings.saved
                                    );
                                }
                                self.gamma = Some(settings.preview);
                                self.settings_error = false;
                            }
                            Err(e) => {
                                if !self.settings_error {
                                    eprintln!("Settings bridge (keeping last gamma): {e}");
                                }
                                self.settings_error = true;
                            }
                        }
                    }
                }
                p.set_gamma(self.gamma);
                let elapsed = self
                    .last_frame
                    .replace(now)
                    .map_or(0., |last| now.duration_since(last).as_secs_f32());
                if let Some(menu) = &mut self.menu {
                    if self.smoke {
                        if self.frames == 5 {
                            menu.focus = Some(0);
                            menu.activate();
                        }
                        if self.frames >= 6 {
                            menu.tick(0.25);
                        }
                        if self.frames == 60 {
                            menu.escape();
                        }
                    } else {
                        menu.tick(elapsed);
                    }
                    p.menu_frame(menu.camera(), menu.vertex());
                }

                if let Some(menu) = &mut self.native_menu {
                    menu.tick(elapsed);
                    if self.smoke {
                        use jade_assets::native_ui::{Action, Page};
                        // Exercise the same actions as interactive input, without saving smoke state.
                        match self.frames {
                            1 => {
                                menu.text("Smoke");
                                menu.accept_text();
                            }
                            3 => {
                                menu.perform(Action::Route(Page::Advanced));
                            }
                            5 => {
                                menu.perform(Action::Choice(1, 70));
                                menu.perform(Action::Choice(2, 0));
                            }
                            6 => {
                                menu.perform(Action::Choice(3, 0));
                            }
                            9 => {
                                menu.perform(Action::Choice(3, 1));
                            }
                            8 => {
                                menu.escape();
                                menu.perform(Action::Answer(2));
                            }
                            10 => {
                                menu.escape();
                                menu.perform(Action::Answer(1));
                            }
                            12 => {
                                menu.perform(Action::Route(Page::Keyboard));
                                menu.scroll(12);
                            }
                            15 => {
                                menu.perform(Action::Route(Page::Sound));
                            }
                            17 => {
                                menu.perform(Action::Route(Page::Game));
                            }
                            18 => {
                                menu.perform(Action::Route(Page::Advanced));
                                menu.perform(Action::Choice(1, 50));
                                menu.perform(Action::Choice(2, 0));
                                menu.perform(Action::Choice(0, 2));
                                menu.escape();
                                menu.perform(Action::Answer(0));
                            }
                            22 => {
                                menu.perform(Action::Route(Page::Effects));
                            }
                            25 => {
                                menu.perform(Action::Route(Page::Gamepad));
                            }
                            28 => {
                                menu.perform(Action::New);
                            }
                            65 => menu.escape(),
                            _ => {}
                        }
                        if (29..65).contains(&self.frames) {
                            menu.tick(0.25);
                        }
                    }
                    // UI widgets edit the draft; only Back -> Yes changes this snapshot.
                    let applied = menu.applied_display();
                    p.set_gamma(Some(applied.gamma));
                    p.set_filter(applied.filter);
                    match p.set_vsync(applied.vsync) {
                        Ok(true) => {}
                        Ok(false) => {
                            menu.settings.values[3] = 1;
                            menu.saved.values[3] = 1;
                            menu.save_requested = true;
                            menu.error = "V-Sync off is unavailable on this surface.".into();
                        }
                        Err(e) => {
                            eprintln!("V-Sync: {e}");
                            self.failed = true;
                            event_loop.exit();
                            return;
                        }
                    }
                    let resolution = applied.resolution;
                    if self.native_resolution != Some(resolution) {
                        self.native_resolution = Some(resolution);
                        let _ = p
                            .window
                            .request_inner_size(PhysicalSize::new(resolution.0, resolution.1));
                    }
                    if menu.save_requested {
                        menu.save_requested = false;
                        if !self.smoke {
                            if let Some(path) = &self.native_state {
                                if let Err(e) = save_native_state(path, &menu.state_text()) {
                                    menu.error = format!("Cannot save OpenJade settings: {e}");
                                    eprintln!("{}", menu.error);
                                }
                            }
                        }
                    }
                    let size = p.window.inner_size();
                    menu.pixel_scale = viewport(size.width, size.height)[2] / 800.;
                    menu.render();
                    p.menu_frame(menu.camera(), None);
                    p.native_ui(&menu.vertices);
                }
                match p.draw() {
                    Ok(true) => self.frames += 1,
                    Ok(false) => {}
                    Err(e) => {
                        eprintln!("Frame: {e:?}");
                        self.failed = true;
                        event_loop.exit();
                        return;
                    }
                }
                if self.smoke {
                    if self.frames == 20 {
                        let _ = p.window.request_inner_size(PhysicalSize::new(
                            if self.native_menu.is_some() {
                                1600
                            } else {
                                1024
                            },
                            if self.native_menu.is_some() {
                                1200
                            } else {
                                720
                            },
                        ));
                    }
                    if self.frames == 40 {
                        let _ = p.window.request_inner_size(PhysicalSize::new(800, 600));
                    }
                    if self.frames >= 80 {
                        event_loop.exit();
                        return;
                    }
                }
                if !p.window.inner_size().width.eq(&0) && p.window.inner_size().height != 0 {
                    p.window.request_redraw();
                }
            }
            _ => {}
        }
    }
    fn exiting(&mut self, _: &ActiveEventLoop) {
        self.presenter.take();
    }
}
fn main() -> std::process::ExitCode {
    let mut args: Vec<_> = std::env::args().skip(1).collect();
    let mut scene = if let Some(i) = args.iter().position(|s| s == "--scene") {
        if i + 1 >= args.len() || args[i + 1].starts_with("--") {
            eprintln!("--scene requires a package path");
            return std::process::ExitCode::FAILURE;
        }
        let path = args.remove(i + 1);
        args.remove(i);
        match jade_assets::Scene::load(std::path::Path::new(&path)) {
            Ok(scene) => {
                println!(
                    "Scene: {} triangles, {} texture layers, vertical FOV {:.5}",
                    scene.vertices.len() / 27,
                    scene.layers,
                    scene.camera[12]
                );
                Some(scene)
            }
            Err(e) => {
                eprintln!("Scene {path}: {e}");
                return std::process::ExitCode::FAILURE;
            }
        }
    } else {
        None
    };
    if let Some(i) = args.iter().position(|s| s == "--texture-filter") {
        let filter = match args.get(i + 1).map(String::as_str) {
            Some("nearest") => jade_assets::TextureFilter::Nearest,
            Some("linear") => jade_assets::TextureFilter::Linear,
            Some("trilinear") => jade_assets::TextureFilter::Trilinear,
            _ => {
                eprintln!("--texture-filter requires nearest, linear or trilinear");
                return std::process::ExitCode::FAILURE;
            }
        };
        let Some(scene) = &mut scene else {
            eprintln!("--texture-filter requires --scene");
            return std::process::ExitCode::FAILURE;
        };
        scene.filter = filter;
        args.drain(i..i + 2);
    }
    if let Some(scene) = &scene {
        println!("Texture filter: {:?}; original mipmaps unavailable; trilinear generates diagnostic mipmaps. UI uses linear/base-level filtering.", scene.filter);
    }
    if let Some(i) = args.iter().position(|s| s == "--color-pipeline") {
        let mode = match args.get(i + 1).map(String::as_str) {
            Some("srgb") => jade_assets::ColorPipeline::Srgb,
            Some("legacy-unorm") => jade_assets::ColorPipeline::LegacyUnorm,
            _ => {
                eprintln!("--color-pipeline requires srgb or legacy-unorm");
                return std::process::ExitCode::FAILURE;
            }
        };
        let Some(scene) = &mut scene else {
            eprintln!("--color-pipeline requires --scene");
            return std::process::ExitCode::FAILURE;
        };
        scene.color_pipeline = mode;
        args.drain(i..i + 2);
    }
    if let Some(scene) = &scene {
        println!(
            "Color pipeline: {:?}; diagnostic; OS display gamma is untouched",
            scene.color_pipeline
        );
    }
    let mut gamma = None;
    if let Some(i) = args.iter().position(|s| s == "--gamma") {
        gamma = args
            .get(i + 1)
            .and_then(|s| s.parse::<u8>().ok())
            .filter(|v| *v <= 100);
        if gamma.is_none() {
            eprintln!("--gamma requires an integer 0..100");
            return std::process::ExitCode::FAILURE;
        }
        args.drain(i..i + 2);
    }
    let settings_path = if let Some(i) = args.iter().position(|s| s == "--settings") {
        if gamma.is_some() || args.get(i + 1).is_none_or(|s| s.starts_with("--")) {
            eprintln!("--settings requires a path and excludes --gamma");
            return std::process::ExitCode::FAILURE;
        }
        let path = std::path::PathBuf::from(args.remove(i + 1));
        args.remove(i);
        match jade_assets::settings::GraphicsSettings::load(&path) {
            Ok(settings) => gamma = Some(settings.preview),
            Err(e) => {
                eprintln!("Settings: {e}");
                return std::process::ExitCode::FAILURE;
            }
        }
        Some(path)
    } else {
        None
    };
    println!(
        "Emulated gamma: {:?}; settings bridge: {:?}",
        gamma, settings_path
    );
    let mut native_menu = None;
    let mut native_state = None;
    let menu = if let Some(i) = args.iter().position(|s| s == "--menu") {
        if i + 1 >= args.len() || args[i + 1].starts_with("--") || scene.is_none() {
            eprintln!("--menu requires a bundle path and --scene");
            return std::process::ExitCode::FAILURE;
        }
        let path = args.remove(i + 1);
        args.remove(i);
        let is_native = (|| -> std::io::Result<bool> {
            use std::io::Read;
            let mut magic = [0; 8];
            std::fs::File::open(&path)?.read_exact(&mut magic)?;
            Ok(&magic == b"OJUI0002" || &magic == b"OJUI0003")
        })();
        if matches!(is_native, Ok(true)) {
            if settings_path.is_some() {
                eprintln!("Native menus control gamma directly; omit --settings.");
                return std::process::ExitCode::FAILURE;
            }
            match NativeMenu::load(std::path::Path::new(&path), scene.as_mut().unwrap()) {
                Ok(mut menu) => {
                    let state = std::path::Path::new(&path).with_extension("ojmenu");
                    if state.exists() {
                        match load_native_state(&state).and_then(|s| menu.restore(&s)) {
                            Ok(()) => {}
                            Err(e) => {
                                eprintln!("Native menu state: {e}");
                                return std::process::ExitCode::FAILURE;
                            }
                        }
                    }
                    if let Some(gamma) = gamma {
                        menu.settings.values[1] = gamma as usize;
                        menu.saved.values[1] = gamma as usize;
                    }
                    native_state = Some(state);
                    native_menu = Some(menu);
                    None
                }
                Err(e) => {
                    eprintln!("Native menu: {e}");
                    return std::process::ExitCode::FAILURE;
                }
            }
        } else {
            match Menu::load(std::path::Path::new(&path), scene.as_mut().unwrap()) {
                Ok(menu) => Some(menu),
                Err(e) => {
                    eprintln!("Menu: {e}");
                    return std::process::ExitCode::FAILURE;
                }
            }
        }
    } else {
        None
    };
    if args.iter().any(|s| s == "--help" || s == "-h") {
        println!("jade-viewer [--scene PATH] [--menu BUNDLE] [--texture-filter nearest|linear|trilinear] [--color-pipeline srgb|legacy-unorm] [--gamma 0..100 | --settings PATH] [--validation] [--smoke]\njade-viewer --probe [--validation]\nDefault: diagnostic panel. --scene: decoded research geometry with depth and fixed camera. Smoke resizes twice and exits after 80 frames.");
        return std::process::ExitCode::SUCCESS;
    }
    if args
        .iter()
        .any(|s| !matches!(s.as_str(), "--probe" | "--validation" | "--smoke"))
        || (args.iter().any(|s| s == "--probe")
            && (args.iter().any(|s| s == "--smoke") || scene.is_some()))
    {
        eprintln!("Invalid arguments; use --help");
        return std::process::ExitCode::FAILURE;
    }
    let validation = args.iter().any(|s| s == "--validation");
    if args.iter().any(|s| s == "--probe") {
        return match jade_render_vulkan::probe(validation) {
            Ok(r) => {
                println!("{r:#?}");
                std::process::ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("{e}");
                std::process::ExitCode::FAILURE
            }
        };
    }
    let mut app = App {
        scene,
        menu,
        native_menu,
        native_state,
        gamma,
        settings_path,
        validation,
        smoke: args.iter().any(|s| s == "--smoke"),
        ..Default::default()
    };
    let result = EventLoop::new().and_then(|e| e.run_app(&mut app));
    app.presenter.take();
    println!(
        "Presented frames: {}; validation errors: {}",
        app.frames,
        validation_errors()
    );
    if let Err(e) = &result {
        eprintln!("Event loop: {e}");
    }
    if result.is_err() || app.failed || validation_errors() != 0 {
        std::process::ExitCode::FAILURE
    } else {
        std::process::ExitCode::SUCCESS
    }
}

fn save_native_state(path: &std::path::Path, text: &str) -> std::io::Result<()> {
    use std::io::{Read, Write};
    if path.extension().and_then(|s| s.to_str()) != Some("ojmenu")
        || path.components().any(|c| {
            c.as_os_str().to_str().is_some_and(|s| {
                s.eq_ignore_ascii_case("game") || s.eq_ignore_ascii_case("profiles")
            })
        })
    {
        return Err(std::io::Error::other(
            "State must be an OpenJade .ojmenu file outside game data",
        ));
    }
    if path.exists() {
        let mut magic = [0; 8];
        std::fs::File::open(path)?.read_exact(&mut magic)?;
        if &magic != b"OJMNU001" {
            return Err(std::io::Error::other("Refusing to replace unrelated data"));
        }
    }
    let tmp = path.with_extension(format!("ojmenu.{}.tmp", std::process::id()));
    let mut file = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&tmp)?;
    let result = (|| {
        file.write_all(text.as_bytes())?;
        file.sync_all()?;
        drop(file);
        std::fs::rename(&tmp, path)
    })();
    if result.is_err() {
        let _ = std::fs::remove_file(&tmp);
    }
    result
}

fn load_native_state(path: &std::path::Path) -> std::io::Result<String> {
    use std::io::Read;
    let mut bytes = Vec::new();
    std::fs::File::open(path)?
        .take(8193)
        .read_to_end(&mut bytes)?;
    if bytes.len() > 8192 {
        return Err(std::io::Error::other("Oversized native state"));
    }
    String::from_utf8(bytes).map_err(|_| std::io::Error::other("Invalid native state encoding"))
}

#[cfg(test)]
mod state_file_tests {
    use super::*;
    fn folder() -> std::path::PathBuf {
        let stamp = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "openjade-state-test-{}-{stamp}",
            std::process::id()
        ));
        std::fs::create_dir(&path).unwrap();
        path
    }
    #[test]
    fn replaces_only_owned_state_and_reloads() {
        let dir = folder();
        let path = dir.join("test.ojmenu");
        save_native_state(&path, "OJMNU001\nfirst\n").unwrap();
        save_native_state(&path, "OJMNU001\nsecond\n").unwrap();
        assert_eq!(load_native_state(&path).unwrap(), "OJMNU001\nsecond\n");
        std::fs::write(&path, "unrelated data").unwrap();
        assert!(save_native_state(&path, "OJMNU001\n").is_err());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), "unrelated data");
        std::fs::remove_file(path).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }
    #[test]
    fn rejects_oversize_state_and_does_not_remove_foreign_temp() {
        let dir = folder();
        let path = dir.join("test.ojmenu");
        std::fs::write(&path, vec![b'x'; 8193]).unwrap();
        assert!(load_native_state(&path).is_err());
        std::fs::remove_file(&path).unwrap();
        let temp = path.with_extension(format!("ojmenu.{}.tmp", std::process::id()));
        std::fs::write(&temp, "foreign").unwrap();
        assert!(save_native_state(&path, "OJMNU001\n").is_err());
        assert_eq!(std::fs::read_to_string(&temp).unwrap(), "foreign");
        std::fs::remove_file(temp).unwrap();
        std::fs::remove_dir(dir).unwrap();
    }
}
