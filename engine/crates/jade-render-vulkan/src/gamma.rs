//! Gamma is applied after all scene/UI blending, without changing desktop ramps.
use ash::vk;
use std::io::Cursor;
pub(super) struct GammaPass {
    device: ash::Device,
    image: vk::Image,
    memory: vk::DeviceMemory,
    pub view: vk::ImageView,
    buffer: vk::Buffer,
    buffer_memory: vk::DeviceMemory,
    pool: vk::DescriptorPool,
    set_layout: vk::DescriptorSetLayout,
    set: vk::DescriptorSet,
    layout: vk::PipelineLayout,
    pipeline: vk::Pipeline,
    shaders: Vec<vk::ShaderModule>,
    srgb: bool,
}
impl GammaPass {
    pub unsafe fn new(
        d: &ash::Device,
        instance: &ash::Instance,
        gpu: vk::PhysicalDevice,
        format: vk::Format,
        extent: vk::Extent2D,
    ) -> Result<Self, vk::Result> {
        let mut p = Self {
            device: d.clone(),
            image: vk::Image::null(),
            memory: vk::DeviceMemory::null(),
            view: vk::ImageView::null(),
            buffer: vk::Buffer::null(),
            buffer_memory: vk::DeviceMemory::null(),
            pool: vk::DescriptorPool::null(),
            set_layout: vk::DescriptorSetLayout::null(),
            set: vk::DescriptorSet::null(),
            layout: vk::PipelineLayout::null(),
            pipeline: vk::Pipeline::null(),
            shaders: vec![],
            srgb: matches!(
                format,
                vk::Format::B8G8R8A8_SRGB | vk::Format::R8G8B8A8_SRGB
            ),
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
        p.image = d.create_image(
            &vk::ImageCreateInfo::default()
                .image_type(vk::ImageType::TYPE_2D)
                .format(format)
                .extent(vk::Extent3D {
                    width: extent.width,
                    height: extent.height,
                    depth: 1,
                })
                .mip_levels(1)
                .array_layers(1)
                .samples(vk::SampleCountFlags::TYPE_1)
                .tiling(vk::ImageTiling::OPTIMAL)
                .usage(
                    vk::ImageUsageFlags::COLOR_ATTACHMENT | vk::ImageUsageFlags::INPUT_ATTACHMENT,
                ),
            None,
        )?;
        let req = d.get_image_memory_requirements(p.image);
        p.memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::DEVICE_LOCAL,
                )?),
            None,
        )?;
        d.bind_image_memory(p.image, p.memory, 0)?;
        p.view = d.create_image_view(
            &vk::ImageViewCreateInfo::default()
                .image(p.image)
                .view_type(vk::ImageViewType::TYPE_2D)
                .format(format)
                .subresource_range(
                    vk::ImageSubresourceRange::default()
                        .aspect_mask(vk::ImageAspectFlags::COLOR)
                        .level_count(1)
                        .layer_count(1),
                ),
            None,
        )?;
        p.buffer = d.create_buffer(
            &vk::BufferCreateInfo::default()
                .size(4112)
                .usage(vk::BufferUsageFlags::UNIFORM_BUFFER),
            None,
        )?;
        let req = d.get_buffer_memory_requirements(p.buffer);
        p.buffer_memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
                )?),
            None,
        )?;
        d.bind_buffer_memory(p.buffer, p.buffer_memory, 0)?;
        let bindings = [
            vk::DescriptorSetLayoutBinding::default()
                .binding(0)
                .descriptor_type(vk::DescriptorType::INPUT_ATTACHMENT)
                .descriptor_count(1)
                .stage_flags(vk::ShaderStageFlags::FRAGMENT),
            vk::DescriptorSetLayoutBinding::default()
                .binding(1)
                .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
                .descriptor_count(1)
                .stage_flags(vk::ShaderStageFlags::FRAGMENT),
        ];
        p.set_layout = d.create_descriptor_set_layout(
            &vk::DescriptorSetLayoutCreateInfo::default().bindings(&bindings),
            None,
        )?;
        let sizes = [
            vk::DescriptorPoolSize::default()
                .ty(vk::DescriptorType::INPUT_ATTACHMENT)
                .descriptor_count(1),
            vk::DescriptorPoolSize::default()
                .ty(vk::DescriptorType::UNIFORM_BUFFER)
                .descriptor_count(1),
        ];
        p.pool = d.create_descriptor_pool(
            &vk::DescriptorPoolCreateInfo::default()
                .max_sets(1)
                .pool_sizes(&sizes),
            None,
        )?;
        p.set = d.allocate_descriptor_sets(
            &vk::DescriptorSetAllocateInfo::default()
                .descriptor_pool(p.pool)
                .set_layouts(&[p.set_layout]),
        )?[0];
        let image = [vk::DescriptorImageInfo::default()
            .image_view(p.view)
            .image_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)];
        let buffer = [vk::DescriptorBufferInfo::default()
            .buffer(p.buffer)
            .range(4112)];
        d.update_descriptor_sets(
            &[
                vk::WriteDescriptorSet::default()
                    .dst_set(p.set)
                    .dst_binding(0)
                    .descriptor_type(vk::DescriptorType::INPUT_ATTACHMENT)
                    .image_info(&image),
                vk::WriteDescriptorSet::default()
                    .dst_set(p.set)
                    .dst_binding(1)
                    .descriptor_type(vk::DescriptorType::UNIFORM_BUFFER)
                    .buffer_info(&buffer),
            ],
            &[],
        );
        p.layout = d.create_pipeline_layout(
            &vk::PipelineLayoutCreateInfo::default().set_layouts(&[p.set_layout]),
            None,
        )?;
        Ok(p)
    }
    pub unsafe fn pipeline(&mut self, render_pass: vk::RenderPass) -> Result<(), vk::Result> {
        let d = &self.device;
        for bytes in [
            include_bytes!(concat!(env!("OUT_DIR"), "/gamma.vert.spv")).as_slice(),
            include_bytes!(concat!(env!("OUT_DIR"), "/gamma.frag.spv")).as_slice(),
        ] {
            let code = ash::util::read_spv(&mut Cursor::new(bytes))
                .map_err(|_| vk::Result::ERROR_INITIALIZATION_FAILED)?;
            self.shaders.push(
                d.create_shader_module(&vk::ShaderModuleCreateInfo::default().code(&code), None)?,
            );
        }
        let stages = [
            vk::PipelineShaderStageCreateInfo::default()
                .stage(vk::ShaderStageFlags::VERTEX)
                .module(self.shaders[0])
                .name(c"main"),
            vk::PipelineShaderStageCreateInfo::default()
                .stage(vk::ShaderStageFlags::FRAGMENT)
                .module(self.shaders[1])
                .name(c"main"),
        ];
        let vertex = vk::PipelineVertexInputStateCreateInfo::default();
        let assembly = vk::PipelineInputAssemblyStateCreateInfo::default()
            .topology(vk::PrimitiveTopology::TRIANGLE_LIST);
        let viewport = vk::PipelineViewportStateCreateInfo::default()
            .viewport_count(1)
            .scissor_count(1);
        let raster = vk::PipelineRasterizationStateCreateInfo::default()
            .polygon_mode(vk::PolygonMode::FILL)
            .cull_mode(vk::CullModeFlags::NONE)
            .line_width(1.);
        let samples = vk::PipelineMultisampleStateCreateInfo::default()
            .rasterization_samples(vk::SampleCountFlags::TYPE_1);
        let attachment = [vk::PipelineColorBlendAttachmentState::default()
            .color_write_mask(vk::ColorComponentFlags::RGBA)];
        let blend = vk::PipelineColorBlendStateCreateInfo::default().attachments(&attachment);
        let dynamic = vk::PipelineDynamicStateCreateInfo::default()
            .dynamic_states(&[vk::DynamicState::VIEWPORT, vk::DynamicState::SCISSOR]);
        let info = vk::GraphicsPipelineCreateInfo::default()
            .stages(&stages)
            .vertex_input_state(&vertex)
            .input_assembly_state(&assembly)
            .viewport_state(&viewport)
            .rasterization_state(&raster)
            .multisample_state(&samples)
            .color_blend_state(&blend)
            .dynamic_state(&dynamic)
            .layout(self.layout)
            .render_pass(render_pass)
            .subpass(1);
        match d.create_graphics_pipelines(vk::PipelineCache::null(), &[info], None) {
            Ok(v) => self.pipeline = v[0],
            Err((partial, e)) => {
                for p in partial {
                    d.destroy_pipeline(p, None);
                }
                return Err(e);
            }
        }
        Ok(())
    }
    // Called only after the single in-flight frame fence has completed.
    pub unsafe fn update(&self, value: Option<u8>) -> Result<(), vk::Result> {
        let mut data = [0f32; 1028];
        for (i, v) in jade_assets::settings::gamma_ramp(value.unwrap_or(0))
            .iter()
            .enumerate()
        {
            data[i * 4] = f32::from(*v) / 65535.;
        }
        data[1024] = if value.is_some() { 1. } else { 0. };
        data[1025] = if self.srgb { 1. } else { 0. };
        let ptr =
            self.device
                .map_memory(self.buffer_memory, 0, 4112, vk::MemoryMapFlags::empty())?;
        std::ptr::copy_nonoverlapping(data.as_ptr().cast::<u8>(), ptr.cast(), 4112);
        self.device.unmap_memory(self.buffer_memory);
        Ok(())
    }
    pub unsafe fn draw(&self, command: vk::CommandBuffer, extent: vk::Extent2D) {
        let d = &self.device;
        d.cmd_next_subpass(command, vk::SubpassContents::INLINE);
        d.cmd_set_viewport(
            command,
            0,
            &[vk::Viewport {
                x: 0.,
                y: 0.,
                width: extent.width as f32,
                height: extent.height as f32,
                min_depth: 0.,
                max_depth: 1.,
            }],
        );
        d.cmd_set_scissor(command, 0, &[vk::Rect2D::default().extent(extent)]);
        d.cmd_bind_pipeline(command, vk::PipelineBindPoint::GRAPHICS, self.pipeline);
        d.cmd_bind_descriptor_sets(
            command,
            vk::PipelineBindPoint::GRAPHICS,
            self.layout,
            0,
            &[self.set],
            &[],
        );
        d.cmd_draw(command, 3, 1, 0, 0);
    }
}
impl Drop for GammaPass {
    fn drop(&mut self) {
        unsafe {
            let d = &self.device;
            d.destroy_pipeline(self.pipeline, None);
            d.destroy_pipeline_layout(self.layout, None);
            for s in self.shaders.drain(..) {
                d.destroy_shader_module(s, None);
            }
            d.destroy_descriptor_pool(self.pool, None);
            d.destroy_descriptor_set_layout(self.set_layout, None);
            d.destroy_buffer(self.buffer, None);
            d.free_memory(self.buffer_memory, None);
            d.destroy_image_view(self.view, None);
            d.destroy_image(self.image, None);
            d.free_memory(self.memory, None);
        }
    }
}
