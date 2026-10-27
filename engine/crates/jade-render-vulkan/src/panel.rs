//! Diagnostic textured quad. All resources are owned even on partial initialization.
use ash::vk;
use jade_assets::{Draw, Scene};
use std::io::Cursor;

pub(super) struct Panel {
    device: ash::Device,
    render_pass: vk::RenderPass,
    views: Vec<vk::ImageView>,
    frames: Vec<vk::Framebuffer>,
    image: vk::Image,
    memory: vk::DeviceMemory,
    texture_view: vk::ImageView,
    staging: vk::Buffer,
    staging_memory: vk::DeviceMemory,
    sampler: vk::Sampler,
    descriptors: vk::DescriptorPool,
    set_layout: vk::DescriptorSetLayout,
    set: vk::DescriptorSet,
    layout: vk::PipelineLayout,
    pipeline: vk::Pipeline,
    blended: Vec<vk::Pipeline>,
    extra_samplers: Vec<vk::Sampler>,
    draws: Vec<Draw>,
    shaders: Vec<vk::ShaderModule>,
    extent: vk::Extent2D,
    vertex_buffer: vk::Buffer,
    vertex_memory: vk::DeviceMemory,
    vertex_count: u32,
    depth: vk::Image,
    depth_memory: vk::DeviceMemory,
    depth_view: vk::ImageView,
    camera: Option<[f32; 20]>,
}
impl Panel {
    // SAFETY: caller owns the device, waits for idle before destruction, and supplies
    // an idle command buffer. This module never outlives the parent's logical device.
    #[allow(clippy::too_many_arguments)] // Explicit Vulkan owner and swapchain inputs.
    pub(super) unsafe fn new(
        d: &ash::Device,
        instance: &ash::Instance,
        gpu: vk::PhysicalDevice,
        images: &[vk::Image],
        format: vk::Format,
        extent: vk::Extent2D,
        command: vk::CommandBuffer,
        queue: vk::Queue,
        scene: Option<&Scene>,
    ) -> Result<Self, vk::Result> {
        let mut p = Self {
            device: d.clone(),
            render_pass: vk::RenderPass::null(),
            views: vec![],
            frames: vec![],
            image: vk::Image::null(),
            memory: vk::DeviceMemory::null(),
            texture_view: vk::ImageView::null(),
            staging: vk::Buffer::null(),
            staging_memory: vk::DeviceMemory::null(),
            sampler: vk::Sampler::null(),
            descriptors: vk::DescriptorPool::null(),
            set_layout: vk::DescriptorSetLayout::null(),
            set: vk::DescriptorSet::null(),
            layout: vk::PipelineLayout::null(),
            pipeline: vk::Pipeline::null(),
            blended: vec![],
            extra_samplers: vec![],
            draws: scene.map_or_else(Vec::new, |s| s.draws.clone()),
            shaders: vec![],
            extent,
            vertex_buffer: vk::Buffer::null(),
            vertex_memory: vk::DeviceMemory::null(),
            vertex_count: scene.map_or(6, |s| (s.vertices.len() / 9) as u32),
            depth: vk::Image::null(),
            depth_memory: vk::DeviceMemory::null(),
            depth_view: vk::ImageView::null(),
            camera: scene.map(|s| s.camera_constants(extent.width as f32 / extent.height as f32)),
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
        let fallback = if scene.is_none() { texture() } else { vec![] };
        let pixels = scene.map_or(fallback.as_slice(), |s| s.pixels.as_slice());
        let (width, height, layers) =
            scene.map_or((128, 128, 1), |s| (s.width, s.height, s.layers));
        let limits = instance.get_physical_device_properties(gpu).limits;
        if width > limits.max_image_dimension2_d
            || height > limits.max_image_dimension2_d
            || layers > limits.max_image_array_layers
        {
            return Err(vk::Result::ERROR_FORMAT_NOT_SUPPORTED);
        }
        if let Some(scene) = scene {
            let bytes: Vec<u8> = scene
                .vertices
                .iter()
                .flat_map(|v| v.to_ne_bytes())
                .collect();
            p.vertex_buffer = d.create_buffer(
                &vk::BufferCreateInfo::default()
                    .size(bytes.len() as u64)
                    .usage(vk::BufferUsageFlags::VERTEX_BUFFER)
                    .sharing_mode(vk::SharingMode::EXCLUSIVE),
                None,
            )?;
            let req = d.get_buffer_memory_requirements(p.vertex_buffer);
            p.vertex_memory = d.allocate_memory(
                &vk::MemoryAllocateInfo::default()
                    .allocation_size(req.size)
                    .memory_type_index(memory_type(
                        req.memory_type_bits,
                        vk::MemoryPropertyFlags::HOST_VISIBLE
                            | vk::MemoryPropertyFlags::HOST_COHERENT,
                    )?),
                None,
            )?;
            d.bind_buffer_memory(p.vertex_buffer, p.vertex_memory, 0)?;
            let mapped = d.map_memory(
                p.vertex_memory,
                0,
                bytes.len() as u64,
                vk::MemoryMapFlags::empty(),
            )?;
            std::ptr::copy_nonoverlapping(bytes.as_ptr(), mapped.cast(), bytes.len());
            d.unmap_memory(p.vertex_memory);
        }
        let depth_format = [vk::Format::D32_SFLOAT, vk::Format::D16_UNORM]
            .into_iter()
            .find(|&f| {
                instance
                    .get_physical_device_format_properties(gpu, f)
                    .optimal_tiling_features
                    .contains(vk::FormatFeatureFlags::DEPTH_STENCIL_ATTACHMENT)
            })
            .ok_or(vk::Result::ERROR_FORMAT_NOT_SUPPORTED)?;
        p.depth = d.create_image(
            &vk::ImageCreateInfo::default()
                .image_type(vk::ImageType::TYPE_2D)
                .format(depth_format)
                .extent(vk::Extent3D {
                    width: extent.width,
                    height: extent.height,
                    depth: 1,
                })
                .mip_levels(1)
                .array_layers(1)
                .samples(vk::SampleCountFlags::TYPE_1)
                .tiling(vk::ImageTiling::OPTIMAL)
                .usage(vk::ImageUsageFlags::DEPTH_STENCIL_ATTACHMENT)
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
            None,
        )?;
        let req = d.get_image_memory_requirements(p.depth);
        p.depth_memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::DEVICE_LOCAL,
                )?),
            None,
        )?;
        d.bind_image_memory(p.depth, p.depth_memory, 0)?;
        p.depth_view = d.create_image_view(
            &vk::ImageViewCreateInfo::default()
                .image(p.depth)
                .view_type(vk::ImageViewType::TYPE_2D)
                .format(depth_format)
                .subresource_range(
                    vk::ImageSubresourceRange::default()
                        .aspect_mask(vk::ImageAspectFlags::DEPTH)
                        .level_count(1)
                        .layer_count(1),
                ),
            None,
        )?;
        p.staging = d.create_buffer(
            &vk::BufferCreateInfo::default()
                .size(pixels.len() as u64)
                .usage(vk::BufferUsageFlags::TRANSFER_SRC)
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
            None,
        )?;
        let req = d.get_buffer_memory_requirements(p.staging);
        p.staging_memory = d.allocate_memory(
            &vk::MemoryAllocateInfo::default()
                .allocation_size(req.size)
                .memory_type_index(memory_type(
                    req.memory_type_bits,
                    vk::MemoryPropertyFlags::HOST_VISIBLE | vk::MemoryPropertyFlags::HOST_COHERENT,
                )?),
            None,
        )?;
        d.bind_buffer_memory(p.staging, p.staging_memory, 0)?;
        let mapped = d.map_memory(
            p.staging_memory,
            0,
            pixels.len() as u64,
            vk::MemoryMapFlags::empty(),
        )?;
        std::ptr::copy_nonoverlapping(pixels.as_ptr(), mapped.cast(), pixels.len());
        d.unmap_memory(p.staging_memory);
        p.image = d.create_image(
            &vk::ImageCreateInfo::default()
                .image_type(vk::ImageType::TYPE_2D)
                .format(vk::Format::R8G8B8A8_SRGB)
                .extent(vk::Extent3D {
                    width,
                    height,
                    depth: 1,
                })
                .mip_levels(1)
                .array_layers(layers)
                .samples(vk::SampleCountFlags::TYPE_1)
                .tiling(vk::ImageTiling::OPTIMAL)
                .usage(vk::ImageUsageFlags::TRANSFER_DST | vk::ImageUsageFlags::SAMPLED)
                .sharing_mode(vk::SharingMode::EXCLUSIVE),
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
        let range = vk::ImageSubresourceRange::default()
            .aspect_mask(vk::ImageAspectFlags::COLOR)
            .level_count(1)
            .layer_count(layers);
        d.reset_command_buffer(command, vk::CommandBufferResetFlags::empty())?;
        d.begin_command_buffer(
            command,
            &vk::CommandBufferBeginInfo::default()
                .flags(vk::CommandBufferUsageFlags::ONE_TIME_SUBMIT),
        )?;
        let barrier = vk::ImageMemoryBarrier::default()
            .image(p.image)
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
            p.staging,
            p.image,
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
        d.cmd_pipeline_barrier(
            command,
            vk::PipelineStageFlags::TRANSFER,
            vk::PipelineStageFlags::FRAGMENT_SHADER,
            vk::DependencyFlags::empty(),
            &[],
            &[],
            &[barrier
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
        p.texture_view = d.create_image_view(
            &vk::ImageViewCreateInfo::default()
                .image(p.image)
                .view_type(if scene.is_some() {
                    vk::ImageViewType::TYPE_2D_ARRAY
                } else {
                    vk::ImageViewType::TYPE_2D
                })
                .format(vk::Format::R8G8B8A8_SRGB)
                .subresource_range(range),
            None,
        )?;
        p.sampler = d.create_sampler(
            &vk::SamplerCreateInfo::default()
                .mag_filter(vk::Filter::NEAREST)
                .min_filter(vk::Filter::NEAREST)
                .address_mode_u(if scene.is_some() {
                    vk::SamplerAddressMode::REPEAT
                } else {
                    vk::SamplerAddressMode::CLAMP_TO_EDGE
                })
                .address_mode_v(if scene.is_some() {
                    vk::SamplerAddressMode::REPEAT
                } else {
                    vk::SamplerAddressMode::CLAMP_TO_EDGE
                })
                .address_mode_w(vk::SamplerAddressMode::CLAMP_TO_EDGE),
            None,
        )?;
        for clamp_v in [false, true] {
            p.extra_samplers.push(
                d.create_sampler(
                    &vk::SamplerCreateInfo::default()
                        .mag_filter(vk::Filter::LINEAR)
                        .min_filter(vk::Filter::LINEAR)
                        .address_mode_u(vk::SamplerAddressMode::REPEAT)
                        .address_mode_v(if clamp_v {
                            vk::SamplerAddressMode::CLAMP_TO_EDGE
                        } else {
                            vk::SamplerAddressMode::REPEAT
                        })
                        .address_mode_w(vk::SamplerAddressMode::CLAMP_TO_EDGE),
                    None,
                )?,
            );
        }
        let bindings: Vec<_> = (0..3)
            .map(|binding| {
                vk::DescriptorSetLayoutBinding::default()
                    .binding(binding)
                    .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                    .descriptor_count(1)
                    .stage_flags(vk::ShaderStageFlags::FRAGMENT)
            })
            .collect();
        p.set_layout = d.create_descriptor_set_layout(
            &vk::DescriptorSetLayoutCreateInfo::default().bindings(&bindings),
            None,
        )?;
        p.descriptors = d.create_descriptor_pool(
            &vk::DescriptorPoolCreateInfo::default()
                .max_sets(1)
                .pool_sizes(&[vk::DescriptorPoolSize::default()
                    .ty(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                    .descriptor_count(3)]),
            None,
        )?;
        p.set = d.allocate_descriptor_sets(
            &vk::DescriptorSetAllocateInfo::default()
                .descriptor_pool(p.descriptors)
                .set_layouts(&[p.set_layout]),
        )?[0];
        for (binding, sampler) in [p.sampler, p.extra_samplers[0], p.extra_samplers[1]]
            .into_iter()
            .enumerate()
        {
            let info = [vk::DescriptorImageInfo::default()
                .sampler(sampler)
                .image_view(p.texture_view)
                .image_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)];
            d.update_descriptor_sets(
                &[vk::WriteDescriptorSet::default()
                    .dst_set(p.set)
                    .dst_binding(binding as u32)
                    .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                    .image_info(&info)],
                &[],
            );
        }
        p.layout = d.create_pipeline_layout(
            &vk::PipelineLayoutCreateInfo::default()
                .set_layouts(&[p.set_layout])
                .push_constant_ranges(&[
                    vk::PushConstantRange::default()
                        .stage_flags(vk::ShaderStageFlags::VERTEX)
                        .size(80),
                    vk::PushConstantRange::default()
                        .stage_flags(vk::ShaderStageFlags::FRAGMENT)
                        .offset(80)
                        .size(32),
                ]),
            None,
        )?;
        let attachment = [
            vk::AttachmentDescription::default()
                .format(format)
                .samples(vk::SampleCountFlags::TYPE_1)
                .load_op(vk::AttachmentLoadOp::CLEAR)
                .store_op(vk::AttachmentStoreOp::STORE)
                .stencil_load_op(vk::AttachmentLoadOp::DONT_CARE)
                .stencil_store_op(vk::AttachmentStoreOp::DONT_CARE)
                .initial_layout(vk::ImageLayout::UNDEFINED)
                .final_layout(vk::ImageLayout::PRESENT_SRC_KHR),
            vk::AttachmentDescription::default()
                .format(depth_format)
                .samples(vk::SampleCountFlags::TYPE_1)
                .load_op(vk::AttachmentLoadOp::CLEAR)
                .store_op(vk::AttachmentStoreOp::DONT_CARE)
                .stencil_load_op(vk::AttachmentLoadOp::DONT_CARE)
                .stencil_store_op(vk::AttachmentStoreOp::DONT_CARE)
                .initial_layout(vk::ImageLayout::UNDEFINED)
                .final_layout(vk::ImageLayout::DEPTH_STENCIL_ATTACHMENT_OPTIMAL),
        ];
        let reference = [vk::AttachmentReference::default()
            .attachment(0)
            .layout(vk::ImageLayout::COLOR_ATTACHMENT_OPTIMAL)];
        let depth_ref = vk::AttachmentReference::default()
            .attachment(1)
            .layout(vk::ImageLayout::DEPTH_STENCIL_ATTACHMENT_OPTIMAL);
        let subpass = [vk::SubpassDescription::default()
            .pipeline_bind_point(vk::PipelineBindPoint::GRAPHICS)
            .color_attachments(&reference)
            .depth_stencil_attachment(&depth_ref)];
        let dependencies = [vk::SubpassDependency::default()
            .src_subpass(vk::SUBPASS_EXTERNAL)
            .dst_subpass(0)
            .src_stage_mask(
                vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT
                    | vk::PipelineStageFlags::LATE_FRAGMENT_TESTS,
            )
            .dst_stage_mask(
                vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT
                    | vk::PipelineStageFlags::EARLY_FRAGMENT_TESTS,
            )
            .src_access_mask(vk::AccessFlags::DEPTH_STENCIL_ATTACHMENT_WRITE)
            .dst_access_mask(
                vk::AccessFlags::COLOR_ATTACHMENT_WRITE
                    | vk::AccessFlags::DEPTH_STENCIL_ATTACHMENT_WRITE,
            )];
        p.render_pass = d.create_render_pass(
            &vk::RenderPassCreateInfo::default()
                .attachments(&attachment)
                .subpasses(&subpass)
                .dependencies(&dependencies),
            None,
        )?;
        for &image in images {
            let view = d.create_image_view(
                &vk::ImageViewCreateInfo::default()
                    .image(image)
                    .view_type(vk::ImageViewType::TYPE_2D)
                    .format(format)
                    .subresource_range(range.layer_count(1)),
                None,
            )?;
            p.views.push(view);
            p.frames.push(
                d.create_framebuffer(
                    &vk::FramebufferCreateInfo::default()
                        .render_pass(p.render_pass)
                        .attachments(&[view, p.depth_view])
                        .width(extent.width)
                        .height(extent.height)
                        .layers(1),
                    None,
                )?,
            );
        }
        let programs = if scene.is_some() {
            [
                include_bytes!(concat!(env!("OUT_DIR"), "/scene.vert.spv")).as_slice(),
                include_bytes!(concat!(env!("OUT_DIR"), "/scene.frag.spv")).as_slice(),
            ]
        } else {
            [
                include_bytes!(concat!(env!("OUT_DIR"), "/panel.vert.spv")).as_slice(),
                include_bytes!(concat!(env!("OUT_DIR"), "/panel.frag.spv")).as_slice(),
            ]
        };
        for bytes in programs {
            let code = ash::util::read_spv(&mut Cursor::new(bytes))
                .map_err(|_| vk::Result::ERROR_INITIALIZATION_FAILED)?;
            p.shaders.push(
                d.create_shader_module(&vk::ShaderModuleCreateInfo::default().code(&code), None)?,
            );
        }
        let stages = [
            vk::PipelineShaderStageCreateInfo::default()
                .stage(vk::ShaderStageFlags::VERTEX)
                .module(p.shaders[0])
                .name(c"main"),
            vk::PipelineShaderStageCreateInfo::default()
                .stage(vk::ShaderStageFlags::FRAGMENT)
                .module(p.shaders[1])
                .name(c"main"),
        ];
        let bindings = [vk::VertexInputBindingDescription::default()
            .binding(0)
            .stride(36)
            .input_rate(vk::VertexInputRate::VERTEX)];
        let attributes = [
            vk::VertexInputAttributeDescription::default()
                .location(0)
                .binding(0)
                .format(vk::Format::R32G32B32_SFLOAT)
                .offset(0),
            vk::VertexInputAttributeDescription::default()
                .location(1)
                .binding(0)
                .format(vk::Format::R32G32_SFLOAT)
                .offset(12),
            vk::VertexInputAttributeDescription::default()
                .location(2)
                .binding(0)
                .format(vk::Format::R32G32B32_SFLOAT)
                .offset(20),
            vk::VertexInputAttributeDescription::default()
                .location(3)
                .binding(0)
                .format(vk::Format::R32_SFLOAT)
                .offset(32),
        ];
        let vertex = if scene.is_some() {
            vk::PipelineVertexInputStateCreateInfo::default()
                .vertex_binding_descriptions(&bindings)
                .vertex_attribute_descriptions(&attributes)
        } else {
            vk::PipelineVertexInputStateCreateInfo::default()
        };
        let depth_state = vk::PipelineDepthStencilStateCreateInfo::default()
            .depth_test_enable(scene.is_some())
            .depth_write_enable(scene.is_some())
            .depth_compare_op(vk::CompareOp::LESS_OR_EQUAL);
        let assembly = vk::PipelineInputAssemblyStateCreateInfo::default()
            .topology(vk::PrimitiveTopology::TRIANGLE_LIST);
        let viewport = vk::PipelineViewportStateCreateInfo::default()
            .viewport_count(1)
            .scissor_count(1);
        let raster = vk::PipelineRasterizationStateCreateInfo::default()
            .polygon_mode(vk::PolygonMode::FILL)
            .cull_mode(vk::CullModeFlags::NONE)
            .line_width(1.0);
        let samples = vk::PipelineMultisampleStateCreateInfo::default()
            .rasterization_samples(vk::SampleCountFlags::TYPE_1);
        let blend_attachment = [vk::PipelineColorBlendAttachmentState::default()
            .color_write_mask(vk::ColorComponentFlags::RGBA)];
        let blend = vk::PipelineColorBlendStateCreateInfo::default().attachments(&blend_attachment);
        let dynamics = [vk::DynamicState::VIEWPORT, vk::DynamicState::SCISSOR];
        let dynamic = vk::PipelineDynamicStateCreateInfo::default().dynamic_states(&dynamics);
        let pipeline = vk::GraphicsPipelineCreateInfo::default()
            .stages(&stages)
            .vertex_input_state(&vertex)
            .input_assembly_state(&assembly)
            .viewport_state(&viewport)
            .rasterization_state(&raster)
            .multisample_state(&samples)
            .color_blend_state(&blend)
            .depth_stencil_state(&depth_state)
            .dynamic_state(&dynamic)
            .layout(p.layout)
            .render_pass(p.render_pass);
        match d.create_graphics_pipelines(vk::PipelineCache::null(), &[pipeline], None) {
            Ok(v) => p.pipeline = v[0],
            Err((partial, error)) => {
                for handle in partial {
                    d.destroy_pipeline(handle, None);
                }
                return Err(error);
            }
        }
        if scene.is_some() {
            for destination in [vk::BlendFactor::ONE_MINUS_SRC_ALPHA, vk::BlendFactor::ONE] {
                let attachment = [vk::PipelineColorBlendAttachmentState::default()
                    .blend_enable(true)
                    .src_color_blend_factor(vk::BlendFactor::SRC_ALPHA)
                    .dst_color_blend_factor(destination)
                    .color_blend_op(vk::BlendOp::ADD)
                    .src_alpha_blend_factor(vk::BlendFactor::ONE)
                    .dst_alpha_blend_factor(vk::BlendFactor::ONE_MINUS_SRC_ALPHA)
                    .alpha_blend_op(vk::BlendOp::ADD)
                    .color_write_mask(vk::ColorComponentFlags::RGBA)];
                let blend =
                    vk::PipelineColorBlendStateCreateInfo::default().attachments(&attachment);
                let depth = depth_state.depth_write_enable(false);
                let info = pipeline
                    .color_blend_state(&blend)
                    .depth_stencil_state(&depth);
                match d.create_graphics_pipelines(vk::PipelineCache::null(), &[info], None) {
                    Ok(v) => p.blended.push(v[0]),
                    Err((partial, error)) => {
                        for handle in partial {
                            d.destroy_pipeline(handle, None);
                        }
                        return Err(error);
                    }
                }
            }
        }
        Ok(p)
    }
    pub(super) unsafe fn draw(&self, command: vk::CommandBuffer, index: usize) {
        let d = &self.device;
        let rect = vk::Rect2D::default().extent(self.extent);
        let clear = [
            vk::ClearValue {
                color: vk::ClearColorValue {
                    float32: [0.025, 0.065, 0.09, 1.0],
                },
            },
            vk::ClearValue {
                depth_stencil: vk::ClearDepthStencilValue {
                    depth: 1.,
                    stencil: 0,
                },
            },
        ];
        d.cmd_begin_render_pass(
            command,
            &vk::RenderPassBeginInfo::default()
                .render_pass(self.render_pass)
                .framebuffer(self.frames[index])
                .render_area(rect)
                .clear_values(&clear),
            vk::SubpassContents::INLINE,
        );
        let side = self.extent.width.min(self.extent.height) as f32 * 0.7;
        d.cmd_set_viewport(
            command,
            0,
            &[vk::Viewport {
                x: (self.extent.width as f32 - side) * 0.5,
                y: (self.extent.height as f32 - side) * 0.5,
                width: side,
                height: side,
                min_depth: 0.0,
                max_depth: 1.0,
            }],
        );
        if let Some(camera) = self.camera {
            d.cmd_set_viewport(
                command,
                0,
                &[vk::Viewport {
                    x: 0.,
                    y: 0.,
                    width: self.extent.width as f32,
                    height: self.extent.height as f32,
                    min_depth: 0.,
                    max_depth: 1.,
                }],
            );
            let bytes: Vec<u8> = camera.iter().flat_map(|v| v.to_ne_bytes()).collect();
            d.cmd_push_constants(
                command,
                self.layout,
                vk::ShaderStageFlags::VERTEX,
                0,
                &bytes,
            );
            d.cmd_bind_vertex_buffers(command, 0, &[self.vertex_buffer], &[0]);
        }
        d.cmd_set_scissor(command, 0, &[rect]);
        d.cmd_bind_pipeline(command, vk::PipelineBindPoint::GRAPHICS, self.pipeline);
        d.cmd_bind_descriptor_sets(
            command,
            vk::PipelineBindPoint::GRAPHICS,
            self.layout,
            0,
            &[self.set],
            &[],
        );
        if self.camera.is_some() {
            for draw in &self.draws {
                let pipeline = match draw.blend {
                    1 => self.blended[0],
                    6 => self.blended[1],
                    _ => self.pipeline,
                };
                d.cmd_bind_pipeline(command, vk::PipelineBindPoint::GRAPHICS, pipeline);
                let bytes: Vec<u8> = draw
                    .parameters
                    .iter()
                    .flat_map(|v| v.to_ne_bytes())
                    .collect();
                d.cmd_push_constants(
                    command,
                    self.layout,
                    vk::ShaderStageFlags::FRAGMENT,
                    80,
                    &bytes,
                );
                d.cmd_draw(command, draw.count, 1, draw.first, 0);
            }
        } else {
            d.cmd_draw(command, self.vertex_count, 1, 0, 0);
        }
        d.cmd_end_render_pass(command);
    }
}
impl Drop for Panel {
    fn drop(&mut self) {
        // Parent waits for the device before dropping this owner.
        unsafe {
            let d = &self.device;
            for pipeline in self.blended.drain(..) {
                d.destroy_pipeline(pipeline, None);
            }
            d.destroy_pipeline(self.pipeline, None);
            d.destroy_pipeline_layout(self.layout, None);
            for shader in self.shaders.drain(..) {
                d.destroy_shader_module(shader, None);
            }
            for frame in self.frames.drain(..) {
                d.destroy_framebuffer(frame, None);
            }
            d.destroy_render_pass(self.render_pass, None);
            d.destroy_image_view(self.depth_view, None);
            d.destroy_image(self.depth, None);
            d.free_memory(self.depth_memory, None);
            d.destroy_buffer(self.vertex_buffer, None);
            d.free_memory(self.vertex_memory, None);
            for view in self.views.drain(..) {
                d.destroy_image_view(view, None);
            }
            d.destroy_descriptor_pool(self.descriptors, None);
            d.destroy_descriptor_set_layout(self.set_layout, None);
            for sampler in self.extra_samplers.drain(..) {
                d.destroy_sampler(sampler, None);
            }
            d.destroy_sampler(self.sampler, None);
            d.destroy_image_view(self.texture_view, None);
            d.destroy_image(self.image, None);
            d.free_memory(self.memory, None);
            d.destroy_buffer(self.staging, None);
            d.free_memory(self.staging_memory, None);
        }
    }
}
// Original diagnostic pixels: red/green/blue/yellow corners identify UV direction.
fn texture() -> Vec<u8> {
    let mut pixels = Vec::with_capacity(128 * 128 * 4);
    for y in 0..128 {
        for x in 0..128 {
            let color = match (x, y) {
                (0..=23, 0..=23) => [235, 55, 55, 255],
                (104..=127, 0..=23) => [55, 220, 95, 255],
                (0..=23, 104..=127) => [55, 110, 245, 255],
                (104..=127, 104..=127) => [245, 210, 45, 255],
                _ if (x / 16 + y / 16) % 2 == 0 => [225, 225, 225, 255],
                _ => [45, 55, 65, 255],
            };
            pixels.extend_from_slice(&color);
        }
    }
    pixels
}
