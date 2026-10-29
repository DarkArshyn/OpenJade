//! Per-texture image ownership. Generated mipmaps are diagnostic, not original assets.
use ash::vk;
pub(super) struct Texture {
    device: ash::Device,
    image: vk::Image,
    memory: vk::DeviceMemory,
    staging: vk::Buffer,
    staging_memory: vk::DeviceMemory,
    pub texture_view: vk::ImageView,
}
impl Texture {
    #[allow(clippy::too_many_arguments)]
    pub unsafe fn new(
        d: &ash::Device,
        instance: &ash::Instance,
        gpu: vk::PhysicalDevice,
        command: vk::CommandBuffer,
        queue: vk::Queue,
        width: u32,
        height: u32,
        pixels: &[u8],
        array: bool,
        mips: bool,
        srgb: bool,
    ) -> Result<Self, vk::Result> {
        let mut t = Self {
            device: d.clone(),
            image: vk::Image::null(),
            memory: vk::DeviceMemory::null(),
            staging: vk::Buffer::null(),
            staging_memory: vk::DeviceMemory::null(),
            texture_view: vk::ImageView::null(),
        };
        let format = if srgb {
            vk::Format::R8G8B8A8_SRGB
        } else {
            vk::Format::R8G8B8A8_UNORM
        };
        let layers = 1;
        let levels = if mips {
            32 - width.max(height).leading_zeros()
        } else {
            1
        };
        let props = instance.get_physical_device_memory_properties(gpu);
        let memory_type = |bits: u32, flags: vk::MemoryPropertyFlags| {
            (0..props.memory_type_count)
                .find(|&i| {
                    bits & (1 << i) != 0
                        && props.memory_types[i as usize]
                            .property_flags
                            .contains(flags)
                })
                .ok_or(vk::Result::ERROR_FEATURE_NOT_PRESENT)
        };
        let features = instance
            .get_physical_device_format_properties(gpu, format)
            .optimal_tiling_features;
        if mips
            && !features.contains(
                vk::FormatFeatureFlags::BLIT_SRC
                    | vk::FormatFeatureFlags::BLIT_DST
                    | vk::FormatFeatureFlags::SAMPLED_IMAGE_FILTER_LINEAR,
            )
        {
            return Err(vk::Result::ERROR_FORMAT_NOT_SUPPORTED);
        }
        t.staging = d.create_buffer(
            &vk::BufferCreateInfo::default()
                .size(pixels.len() as u64)
                .usage(vk::BufferUsageFlags::TRANSFER_SRC)
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
            None,
        )?;
        let req = d.get_buffer_memory_requirements(t.staging);
        t.staging_memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
                )?),
            None,
        )?;
        d.bind_buffer_memory(t.staging, t.staging_memory, 0)?;
        let mapped = d.map_memory(
            t.staging_memory,
            0,
            pixels.len() as u64,
            vk::MemoryMapFlags::empty(),
        )?;
        std::ptr::copy_nonoverlapping(pixels.as_ptr(), mapped.cast(), pixels.len());
        d.unmap_memory(t.staging_memory);
        t.image = d.create_image(
            &vk::ImageCreateInfo::default()
                .image_type(vk::ImageType::TYPE_2D)
                .format(format)
                .extent(vk::Extent3D {
                    width,
                    height,
                    depth: 1,
                })
                .mip_levels(levels)
                .array_layers(layers)
                .samples(vk::SampleCountFlags::TYPE_1)
                .tiling(vk::ImageTiling::OPTIMAL)
                .usage(
                    vk::ImageUsageFlags::TRANSFER_DST
                        | vk::ImageUsageFlags::TRANSFER_SRC
                        | vk::ImageUsageFlags::SAMPLED,
                )
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
            None,
        )?;
        let req = d.get_image_memory_requirements(t.image);
        t.memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::DEVICE_LOCAL,
                )?),
            None,
        )?;
        d.bind_image_memory(t.image, t.memory, 0)?;
        let range = vk::ImageSubresourceRange::default()
            .aspect_mask(vk::ImageAspectFlags::COLOR)
            .level_count(levels)
            .layer_count(layers);
        d.reset_command_buffer(command, vk::CommandBufferResetFlags::empty())?;
        d.begin_command_buffer(
            command,
            &vk::CommandBufferBeginInfo::default()
                .flags(vk::CommandBufferUsageFlags::ONE_TIME_SUBMIT),
        )?;
        let barrier = vk::ImageMemoryBarrier::default()
            .image(t.image)
            .subresource_range(range)
            .src_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
            .dst_queue_family_index(vk::QUEUE_FAMILY_IGNORED)
            .old_layout(vk::ImageLayout::UNDEFINED)
            .new_layout(vk::ImageLayout::TRANSFER_DST_OPTIMAL)
            .dst_access_mask(vk::AccessFlags::TRANSFER_WRITE);
        d.cmd_pipeline_barrier(
            command,
            vk::PipelineStageFlags::TOP_OF_PIPE,
            vk::PipelineStageFlags::TRANSFER,
            vk::DependencyFlags::empty(),
            &[],
            &[],
            &[barrier],
        );
        d.cmd_copy_buffer_to_image(
            command,
            t.staging,
            t.image,
            vk::ImageLayout::TRANSFER_DST_OPTIMAL,
            &[vk::BufferImageCopy::default()
                .image_subresource(
                    vk::ImageSubresourceLayers::default()
                        .aspect_mask(vk::ImageAspectFlags::COLOR)
                        .layer_count(layers),
                )
                .image_extent(vk::Extent3D {
                    width,
                    height,
                    depth: 1,
                })],
        );
        let mut w = width as i32;
        let mut h = height as i32;
        for level in 1..levels {
            let previous = range.base_mip_level(level - 1).level_count(1);
            d.cmd_pipeline_barrier(
                command,
                vk::PipelineStageFlags::TRANSFER,
                vk::PipelineStageFlags::TRANSFER,
                vk::DependencyFlags::empty(),
                &[],
                &[],
                &[barrier
                    .subresource_range(previous)
                    .old_layout(vk::ImageLayout::TRANSFER_DST_OPTIMAL)
                    .new_layout(vk::ImageLayout::TRANSFER_SRC_OPTIMAL)
                    .src_access_mask(vk::AccessFlags::TRANSFER_WRITE)
                    .dst_access_mask(vk::AccessFlags::TRANSFER_READ)],
            );
            let next_w = (w / 2).max(1);
            let next_h = (h / 2).max(1);
            d.cmd_blit_image(
                command,
                t.image,
                vk::ImageLayout::TRANSFER_SRC_OPTIMAL,
                t.image,
                vk::ImageLayout::TRANSFER_DST_OPTIMAL,
                &[vk::ImageBlit::default()
                    .src_subresource(
                        vk::ImageSubresourceLayers::default()
                            .aspect_mask(vk::ImageAspectFlags::COLOR)
                            .mip_level(level - 1)
                            .layer_count(1),
                    )
                    .src_offsets([vk::Offset3D::default(), vk::Offset3D { x: w, y: h, z: 1 }])
                    .dst_subresource(
                        vk::ImageSubresourceLayers::default()
                            .aspect_mask(vk::ImageAspectFlags::COLOR)
                            .mip_level(level)
                            .layer_count(1),
                    )
                    .dst_offsets([
                        vk::Offset3D::default(),
                        vk::Offset3D {
                            x: next_w,
                            y: next_h,
                            z: 1,
                        },
                    ])],
                vk::Filter::LINEAR,
            );
            d.cmd_pipeline_barrier(
                command,
                vk::PipelineStageFlags::TRANSFER,
                vk::PipelineStageFlags::FRAGMENT_SHADER,
                vk::DependencyFlags::empty(),
                &[],
                &[],
                &[barrier
                    .subresource_range(previous)
                    .old_layout(vk::ImageLayout::TRANSFER_SRC_OPTIMAL)
                    .new_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)
                    .src_access_mask(vk::AccessFlags::TRANSFER_READ)
                    .dst_access_mask(vk::AccessFlags::SHADER_READ)],
            );
            w = next_w;
            h = next_h;
        }
        d.cmd_pipeline_barrier(
            command,
            vk::PipelineStageFlags::TRANSFER,
            vk::PipelineStageFlags::FRAGMENT_SHADER,
            vk::DependencyFlags::empty(),
            &[],
            &[],
            &[barrier
                .subresource_range(range.base_mip_level(levels - 1).level_count(1))
                .old_layout(vk::ImageLayout::TRANSFER_DST_OPTIMAL)
                .new_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)
                .src_access_mask(vk::AccessFlags::TRANSFER_WRITE)
                .dst_access_mask(vk::AccessFlags::SHADER_READ)],
        );
        d.end_command_buffer(command)?;
        d.queue_submit(
            queue,
            &[vk::SubmitInfo::default().command_buffers(&[command])],
            vk::Fence::null(),
        )?;
        d.queue_wait_idle(queue)?;
        t.texture_view = d.create_image_view(
            &vk::ImageViewCreateInfo::default()
                .image(t.image)
                .view_type(if array {
                    vk::ImageViewType::TYPE_2D_ARRAY
                } else {
                    vk::ImageViewType::TYPE_2D
                })
                .format(format)
                .subresource_range(range),
            None,
        )?;
        Ok(t)
    }
}
impl Drop for Texture {
    fn drop(&mut self) {
        unsafe {
            self.device.destroy_image_view(self.texture_view, None);
            self.device.destroy_image(self.image, None);
            self.device.free_memory(self.memory, None);
            self.device.destroy_buffer(self.staging, None);
            self.device.free_memory(self.staging_memory, None);
        }
    }
}
