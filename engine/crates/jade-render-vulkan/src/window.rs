//! Single-frame Vulkan presentation with an original diagnostic textured panel.
#[path = "panel.rs"]
mod panel;
use ash::{vk, Entry};
use jade_assets::Scene;
use panel::Panel;
use raw_window_handle::{HasDisplayHandle, HasWindowHandle};
use std::{
    ffi::CStr,
    sync::{
        atomic::{AtomicUsize, Ordering},
        Arc,
    },
};
use winit::window::Window;

static ERRORS: AtomicUsize = AtomicUsize::new(0);
pub fn validation_errors() -> usize {
    ERRORS.load(Ordering::Relaxed)
}

unsafe extern "system" fn debug(
    severity: vk::DebugUtilsMessageSeverityFlagsEXT,
    _: vk::DebugUtilsMessageTypeFlagsEXT,
    data: *const vk::DebugUtilsMessengerCallbackDataEXT<'_>,
    _: *mut std::ffi::c_void,
) -> vk::Bool32 {
    if severity.contains(vk::DebugUtilsMessageSeverityFlagsEXT::ERROR) {
        ERRORS.fetch_add(1, Ordering::Relaxed);
    }
    if !data.is_null() && !(*data).p_message.is_null() {
        eprintln!(
            "Vulkan {severity:?}: {}",
            CStr::from_ptr((*data).p_message).to_string_lossy()
        );
    }
    vk::FALSE
}

pub struct Presenter {
    // The window and loader outlive every Vulkan child, including on init failure.
    pub window: Arc<Window>,
    _entry: Entry,
    instance: ash::Instance,
    debug_loader: ash::ext::debug_utils::Instance,
    messenger: vk::DebugUtilsMessengerEXT,
    surface_loader: ash::khr::surface::Instance,
    surface: vk::SurfaceKHR,
    physical: vk::PhysicalDevice,
    device: Option<ash::Device>,
    queue: vk::Queue,
    swap_loader: Option<ash::khr::swapchain::Device>,
    swap: vk::SwapchainKHR,
    images: Vec<vk::Image>,
    done: Vec<vk::Semaphore>,
    acquired: vk::Semaphore,
    fence: vk::Fence,
    pool: vk::CommandPool,
    command: vk::CommandBuffer,
    dirty: bool,
    panel: Option<Panel>,
    scene: Option<Scene>,
}

impl Presenter {
    pub fn new(
        window: Arc<Window>,
        validation: bool,
        scene: Option<Scene>,
    ) -> Result<Self, Box<dyn std::error::Error>> {
        // SAFETY: retained Arc keeps native handles alive. Each created handle is
        // immediately owned by Presenter and released in reverse dependency order.
        unsafe {
            let entry = Entry::load()?;
            let display = window.display_handle()?.as_raw();
            let handle = window.window_handle()?.as_raw();
            let mut extensions = ash_window::enumerate_required_extensions(display)?.to_vec();
            let layers = if validation {
                let available = entry.enumerate_instance_layer_properties()?;
                if !available.iter().any(|p| {
                    CStr::from_ptr(p.layer_name.as_ptr()) == c"VK_LAYER_KHRONOS_validation"
                }) {
                    return Err("Validation layer missing".into());
                }
                extensions.push(ash::ext::debug_utils::NAME.as_ptr());
                vec![c"VK_LAYER_KHRONOS_validation".as_ptr()]
            } else {
                vec![]
            };
            let app = vk::ApplicationInfo::default()
                .application_name(c"OpenJade")
                .api_version(vk::API_VERSION_1_0);
            let instance = entry.create_instance(
                &vk::InstanceCreateInfo::default()
                    .application_info(&app)
                    .enabled_extension_names(&extensions)
                    .enabled_layer_names(&layers),
                None,
            )?;
            let mut this = Self {
                debug_loader: ash::ext::debug_utils::Instance::new(&entry, &instance),
                surface_loader: ash::khr::surface::Instance::new(&entry, &instance),
                window,
                _entry: entry,
                instance,
                messenger: vk::DebugUtilsMessengerEXT::null(),
                surface: vk::SurfaceKHR::null(),
                physical: vk::PhysicalDevice::null(),
                device: None,
                queue: vk::Queue::null(),
                swap_loader: None,
                swap: vk::SwapchainKHR::null(),
                images: vec![],
                done: vec![],
                acquired: vk::Semaphore::null(),
                fence: vk::Fence::null(),
                pool: vk::CommandPool::null(),
                command: vk::CommandBuffer::null(),
                dirty: true,
                panel: None,
                scene,
            };
            if validation {
                this.messenger = this.debug_loader.create_debug_utils_messenger(
                    &vk::DebugUtilsMessengerCreateInfoEXT::default()
                        .message_severity(
                            vk::DebugUtilsMessageSeverityFlagsEXT::WARNING
                                | vk::DebugUtilsMessageSeverityFlagsEXT::ERROR,
                        )
                        .message_type(
                            vk::DebugUtilsMessageTypeFlagsEXT::GENERAL
                                | vk::DebugUtilsMessageTypeFlagsEXT::VALIDATION
                                | vk::DebugUtilsMessageTypeFlagsEXT::PERFORMANCE,
                        )
                        .pfn_user_callback(Some(debug)),
                    None,
                )?;
            }
            this.surface =
                ash_window::create_surface(&this._entry, &this.instance, display, handle, None)?;
            let mut selected = None;
            for gpu in this.instance.enumerate_physical_devices()? {
                let ext = this.instance.enumerate_device_extension_properties(gpu)?;
                if !ext
                    .iter()
                    .any(|e| CStr::from_ptr(e.extension_name.as_ptr()) == ash::khr::swapchain::NAME)
                {
                    continue;
                }
                for (i, q) in this
                    .instance
                    .get_physical_device_queue_family_properties(gpu)
                    .iter()
                    .enumerate()
                {
                    if q.queue_count > 0
                        && q.queue_flags.contains(vk::QueueFlags::GRAPHICS)
                        && this.surface_loader.get_physical_device_surface_support(
                            gpu,
                            i as u32,
                            this.surface,
                        )?
                    {
                        selected = Some((gpu, i as u32));
                        break;
                    }
                }
                if selected.is_some() {
                    break;
                }
            }
            let (gpu, family) =
                selected.ok_or("No graphics/present queue with swapchain support")?;
            this.physical = gpu;
            let priorities = [1.0];
            let queues = [vk::DeviceQueueCreateInfo::default()
                .queue_family_index(family)
                .queue_priorities(&priorities)];
            let ext = [ash::khr::swapchain::NAME.as_ptr()];
            let device = this.instance.create_device(
                gpu,
                &vk::DeviceCreateInfo::default()
                    .queue_create_infos(&queues)
                    .enabled_extension_names(&ext),
                None,
            )?;
            this.queue = device.get_device_queue(family, 0);
            this.swap_loader = Some(ash::khr::swapchain::Device::new(&this.instance, &device));
            this.device = Some(device);
            let d = this.device.as_ref().unwrap();
            this.pool = d.create_command_pool(
                &vk::CommandPoolCreateInfo::default()
                    .queue_family_index(family)
                    .flags(vk::CommandPoolCreateFlags::RESET_COMMAND_BUFFER),
                None,
            )?;
            this.command = d.allocate_command_buffers(
                &vk::CommandBufferAllocateInfo::default()
                    .command_pool(this.pool)
                    .level(vk::CommandBufferLevel::PRIMARY)
                    .command_buffer_count(1),
            )?[0];
            this.acquired = d.create_semaphore(&vk::SemaphoreCreateInfo::default(), None)?;
            this.fence = d.create_fence(
                &vk::FenceCreateInfo::default().flags(vk::FenceCreateFlags::SIGNALED),
                None,
            )?;
            let p = this.instance.get_physical_device_properties(gpu);
            println!(
                "Present adapter: {}",
                CStr::from_ptr(p.device_name.as_ptr()).to_string_lossy()
            );
            Ok(this)
        }
    }
    pub fn resize(&mut self) {
        self.dirty = true;
    }
    unsafe fn recreate(&mut self) -> Result<(), vk::Result> {
        let d = self.device.as_ref().unwrap();
        d.device_wait_idle()?;
        self.panel.take();
        for s in self.done.drain(..) {
            d.destroy_semaphore(s, None);
        }
        let loader = self.swap_loader.as_ref().unwrap();
        if self.swap != vk::SwapchainKHR::null() {
            loader.destroy_swapchain(self.swap, None);
            self.swap = vk::SwapchainKHR::null();
        }
        let caps = self
            .surface_loader
            .get_physical_device_surface_capabilities(self.physical, self.surface)?;
        if !caps
            .supported_usage_flags
            .contains(vk::ImageUsageFlags::COLOR_ATTACHMENT)
        {
            return Err(vk::Result::ERROR_FORMAT_NOT_SUPPORTED);
        }
        let formats = self
            .surface_loader
            .get_physical_device_surface_formats(self.physical, self.surface)?;
        let mut format = *formats
            .iter()
            .find(|f| f.format == vk::Format::B8G8R8A8_SRGB)
            .or(formats.first())
            .ok_or(vk::Result::ERROR_FORMAT_NOT_SUPPORTED)?;
        if format.format == vk::Format::UNDEFINED {
            format.format = vk::Format::B8G8R8A8_UNORM;
        }
        let size = self.window.inner_size();
        let extent = if caps.current_extent.width != u32::MAX {
            caps.current_extent
        } else {
            vk::Extent2D {
                width: size
                    .width
                    .clamp(caps.min_image_extent.width, caps.max_image_extent.width),
                height: size
                    .height
                    .clamp(caps.min_image_extent.height, caps.max_image_extent.height),
            }
        };
        let count = if caps.max_image_count == 0 {
            caps.min_image_count + 1
        } else {
            (caps.min_image_count + 1).min(caps.max_image_count)
        };
        let alpha = [
            vk::CompositeAlphaFlagsKHR::OPAQUE,
            vk::CompositeAlphaFlagsKHR::PRE_MULTIPLIED,
            vk::CompositeAlphaFlagsKHR::POST_MULTIPLIED,
            vk::CompositeAlphaFlagsKHR::INHERIT,
        ]
        .into_iter()
        .find(|a| caps.supported_composite_alpha.contains(*a))
        .ok_or(vk::Result::ERROR_FORMAT_NOT_SUPPORTED)?;
        self.swap = loader.create_swapchain(
            &vk::SwapchainCreateInfoKHR::default()
                .surface(self.surface)
                .min_image_count(count)
                .image_format(format.format)
                .image_color_space(format.color_space)
                .image_extent(extent)
                .image_array_layers(1)
                .image_usage(vk::ImageUsageFlags::COLOR_ATTACHMENT)
                .image_sharing_mode(vk::SharingMode::EXCLUSIVE)
                .pre_transform(caps.current_transform)
                .composite_alpha(alpha)
                .present_mode(vk::PresentModeKHR::FIFO)
                .clipped(true),
            None,
        )?;
        self.images = loader.get_swapchain_images(self.swap)?;
        for _ in &self.images {
            self.done
                .push(d.create_semaphore(&vk::SemaphoreCreateInfo::default(), None)?);
        }
        println!(
            "Swapchain {}x{}; {} images",
            extent.width,
            extent.height,
            self.images.len()
        );
        self.panel = Some(Panel::new(
            d,
            &self.instance,
            self.physical,
            &self.images,
            format.format,
            extent,
            self.command,
            self.queue,
            self.scene.as_ref(),
        )?);
        self.dirty = false;
        Ok(())
    }
    pub fn draw(&mut self) -> Result<bool, vk::Result> {
        let size = self.window.inner_size();
        if size.width == 0 || size.height == 0 {
            return Ok(false);
        }
        // SAFETY: one frame in flight. Fence protects command reuse; acquire waits
        // at COLOR_ATTACHMENT_OUTPUT. Render-finished semaphores are allocated per swapchain image.
        unsafe {
            if self.dirty {
                self.recreate()?;
            }
            let d = self.device.as_ref().unwrap();
            let loader = self.swap_loader.as_ref().unwrap();
            d.wait_for_fences(&[self.fence], true, u64::MAX)?;
            let (index, suboptimal) = match loader.acquire_next_image(
                self.swap,
                u64::MAX,
                self.acquired,
                vk::Fence::null(),
            ) {
                Ok(v) => v,
                Err(vk::Result::ERROR_OUT_OF_DATE_KHR) => {
                    self.dirty = true;
                    return Ok(false);
                }
                Err(e) => return Err(e),
            };
            d.reset_command_buffer(self.command, vk::CommandBufferResetFlags::empty())?;
            d.begin_command_buffer(self.command, &vk::CommandBufferBeginInfo::default())?;
            self.panel
                .as_ref()
                .unwrap()
                .draw(self.command, index as usize);
            d.end_command_buffer(self.command)?;
            let wait = [self.acquired];
            let stage = [vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT];
            let cmd = [self.command];
            let signal = [self.done[index as usize]];
            d.reset_fences(&[self.fence])?;
            d.queue_submit(
                self.queue,
                &[vk::SubmitInfo::default()
                    .wait_semaphores(&wait)
                    .wait_dst_stage_mask(&stage)
                    .command_buffers(&cmd)
                    .signal_semaphores(&signal)],
                self.fence,
            )?;
            let swaps = [self.swap];
            let indices = [index];
            match loader.queue_present(
                self.queue,
                &vk::PresentInfoKHR::default()
                    .wait_semaphores(&signal)
                    .swapchains(&swaps)
                    .image_indices(&indices),
            ) {
                Ok(s) => self.dirty |= s || suboptimal,
                Err(vk::Result::ERROR_OUT_OF_DATE_KHR) => self.dirty = true,
                Err(e) => return Err(e),
            }
            Ok(true)
        }
    }
}
impl Drop for Presenter {
    fn drop(&mut self) {
        // SAFETY: idle before freeing GPU resources; null handles are permitted.
        unsafe {
            if let Some(d) = &self.device {
                let _ = d.device_wait_idle();
                self.panel.take();
                for s in self.done.drain(..) {
                    d.destroy_semaphore(s, None);
                }
                d.destroy_fence(self.fence, None);
                d.destroy_semaphore(self.acquired, None);
                d.destroy_command_pool(self.pool, None);
                if let Some(l) = &self.swap_loader {
                    l.destroy_swapchain(self.swap, None);
                }
                d.destroy_device(None);
            }
            self.surface_loader.destroy_surface(self.surface, None);
            if self.messenger != vk::DebugUtilsMessengerEXT::null() {
                self.debug_loader
                    .destroy_debug_utils_messenger(self.messenger, None);
            }
            self.instance.destroy_instance(None);
        }
    }
}
