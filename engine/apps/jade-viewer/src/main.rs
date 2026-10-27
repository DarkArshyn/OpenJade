use jade_render_vulkan::window::{validation_errors, Presenter};
use std::sync::Arc;
use winit::{
    application::ApplicationHandler,
    dpi::PhysicalSize,
    event::WindowEvent,
    event_loop::{ActiveEventLoop, EventLoop},
    window::WindowId,
};

#[derive(Default)]
struct App {
    presenter: Option<Presenter>,
    validation: bool,
    smoke: bool,
    frames: u32,
    failed: bool,
    scene: Option<jade_assets::Scene>,
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
            WindowEvent::CloseRequested => event_loop.exit(),
            WindowEvent::Resized(_) => {
                p.resize();
                p.window.request_redraw();
            }
            WindowEvent::RedrawRequested => {
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
    let scene = if let Some(i) = args.iter().position(|s| s == "--scene") {
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
    if args.iter().any(|s| s == "--help" || s == "-h") {
        println!("jade-viewer [--scene PATH] [--validation] [--smoke]\njade-viewer --probe [--validation]\nDefault: diagnostic panel. --scene: decoded research geometry with depth and fixed camera. Smoke resizes twice and exits after 80 frames.");
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
