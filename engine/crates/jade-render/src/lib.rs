//! Backend-independent diagnostics. No Vulkan types cross this boundary.

#[derive(Debug)]
pub struct AdapterInfo {
    pub name: String,
    pub api_version: (u32, u32, u32),
    pub graphics_queues: usize,
}

#[derive(Debug)]
pub struct ProbeReport {
    pub validation_enabled: bool,
    pub adapters: Vec<AdapterInfo>,
}
