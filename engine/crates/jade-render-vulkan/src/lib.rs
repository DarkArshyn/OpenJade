//! Initial Vulkan loader/instance probe. Rendering is a later milestone.
use ash::{vk, Entry};
use jade_render::{AdapterInfo, ProbeReport};
use std::ffi::{CStr, CString};

pub fn probe(require_validation: bool) -> Result<ProbeReport, String> {
    // SAFETY: Entry owns the dynamically loaded library until all Vulkan objects
    // below have been destroyed. No function pointers escape this call.
    let entry = unsafe { Entry::load() }.map_err(|e| format!("Vulkan loader: {e}"))?;
    let layer = CString::new("VK_LAYER_KHRONOS_validation").unwrap();
    // SAFETY: enumeration has no object lifetime prerequisites beyond Entry.
    let layers = unsafe { entry.enumerate_instance_layer_properties() }
        .map_err(|e| format!("Layer enumeration: {e:?}"))?;
    let available = layers.iter().any(|p| {
        // SAFETY: Vulkan returns a null-terminated fixed-size layer name.
        unsafe { CStr::from_ptr(p.layer_name.as_ptr()) == layer.as_c_str() }
    });
    if require_validation && !available {
        return Err("Requested VK_LAYER_KHRONOS_validation is unavailable".into());
    }
    let name = CString::new("OpenJade Vulkan probe").unwrap();
    let app = vk::ApplicationInfo::default()
        .application_name(&name)
        .engine_name(&name)
        .api_version(vk::API_VERSION_1_0);
    let layer_names = if require_validation {
        vec![layer.as_ptr()]
    } else {
        vec![]
    };
    let info = vk::InstanceCreateInfo::default()
        .application_info(&app)
        .enabled_layer_names(&layer_names);
    // SAFETY: all referenced names and structs remain alive through creation.
    let instance = unsafe { entry.create_instance(&info, None) }
        .map_err(|e| format!("Instance creation: {e:?}"))?;
    let result = (|| {
        // SAFETY: instance is live throughout this closure.
        let devices = unsafe { instance.enumerate_physical_devices() }
            .map_err(|e| format!("Adapter enumeration: {e:?}"))?;
        if devices.is_empty() {
            return Err("No Vulkan adapters found".into());
        }
        let adapters = devices
            .into_iter()
            .map(|device| {
                // SAFETY: device handles were returned by this live instance.
                let p = unsafe { instance.get_physical_device_properties(device) };
                let queues =
                    unsafe { instance.get_physical_device_queue_family_properties(device) };
                let name = unsafe { CStr::from_ptr(p.device_name.as_ptr()) }
                    .to_string_lossy()
                    .into_owned();
                AdapterInfo {
                    name,
                    api_version: (
                        vk::api_version_major(p.api_version),
                        vk::api_version_minor(p.api_version),
                        vk::api_version_patch(p.api_version),
                    ),
                    graphics_queues: queues
                        .iter()
                        .filter(|q| {
                            q.queue_count > 0 && q.queue_flags.contains(vk::QueueFlags::GRAPHICS)
                        })
                        .count(),
                }
            })
            .collect();
        Ok(ProbeReport {
            validation_enabled: require_validation,
            adapters,
        })
    })();
    // SAFETY: no child device or surface was created, and no handles escape.
    unsafe {
        instance.destroy_instance(None);
    }
    result
}

pub mod window;
