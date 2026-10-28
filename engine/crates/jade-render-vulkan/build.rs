use std::{env, path::PathBuf, process::Command};
fn main() {
    println!("cargo:rerun-if-env-changed=VULKAN_SDK");
    let compiler = env::var_os("VULKAN_SDK")
        .map(|p| {
            PathBuf::from(p).join(if cfg!(windows) {
                "Bin/glslc.exe"
            } else {
                "bin/glslc"
            })
        })
        .unwrap_or_else(|| "glslc".into());
    for name in [
        "panel.vert",
        "panel.frag",
        "scene.vert",
        "scene.frag",
        "ui.vert",
    ] {
        let source = PathBuf::from("shaders").join(name);
        println!("cargo:rerun-if-changed={}", source.display());
        let output = PathBuf::from(env::var_os("OUT_DIR").unwrap()).join(format!("{name}.spv"));
        let status = Command::new(&compiler)
            .arg("--target-env=vulkan1.0")
            .arg(&source)
            .arg("-o")
            .arg(output)
            .status()
            .expect("glslc is required: install the Vulkan SDK and set VULKAN_SDK or PATH");
        assert!(status.success(), "Shader compilation failed: {name}");
    }
}
