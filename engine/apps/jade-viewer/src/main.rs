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
    last_frame: Option<Instant>,
    pointer: Option<(f32, f32)>,
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
                if let Some(menu) = &mut self.menu {
                    menu.quit_prompt();
                } else {
                    event_loop.exit();
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
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
            WindowEvent::KeyboardInput { event, .. }
                if event.state == ElementState::Pressed && !event.repeat =>
            {
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
            WindowEvent::Resized(_) => {
                p.resize();
                p.window.request_redraw();
            }
            WindowEvent::RedrawRequested => {
                let now = Instant::now();
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
                        let _ = p.window.request_inner_size(PhysicalSize::new(1024, 720));
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
    let menu = if let Some(i) = args.iter().position(|s| s == "--menu") {
        if i + 1 >= args.len() || args[i + 1].starts_with("--") || scene.is_none() {
            eprintln!("--menu requires a bundle path and --scene");
            return std::process::ExitCode::FAILURE;
        }
        let path = args.remove(i + 1);
        args.remove(i);
        match Menu::load(std::path::Path::new(&path), scene.as_mut().unwrap()) {
            Ok(menu) => Some(menu),
            Err(e) => {
                eprintln!("Menu: {e}");
                return std::process::ExitCode::FAILURE;
            }
        }
    } else {
        None
    };
    if args.iter().any(|s| s == "--help" || s == "-h") {
        println!("jade-viewer [--scene PATH] [--menu BUNDLE] [--validation] [--smoke]\njade-viewer --probe [--validation]\nDefault: diagnostic panel. --scene: decoded research geometry with depth and fixed camera. Smoke resizes twice and exits after 80 frames.");
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
