//! Measured current-frame menu blur, before UI and display gamma.
use ash::vk;
use std::io::Cursor;
#[derive(Default)]
struct Target {
    size: u32,
    image: vk::Image,
    memory: vk::DeviceMemory,
    view: vk::ImageView,
    framebuffer: vk::Framebuffer,
}
pub(super) struct MenuBlur {
    device: ash::Device,
    targets: Vec<Target>,
    clear_pass: vk::RenderPass,
    load_pass: vk::RenderPass,
    pipeline: vk::Pipeline,
    composite: vk::Pipeline,
    additive_pipeline: vk::Pipeline,
    additive: bool,
    layout: vk::PipelineLayout,
    set_layout: vk::DescriptorSetLayout,
    pool: vk::DescriptorPool,
    sets: Vec<vk::DescriptorSet>,
    sampler: vk::Sampler,
    shaders: Vec<vk::ShaderModule>,
}
impl MenuBlur {
    pub unsafe fn new(
        d: &ash::Device,
        instance: &ash::Instance,
        gpu: vk::PhysicalDevice,
        source: vk::ImageView,
        main_pass: vk::RenderPass,
        additive: bool,
    ) -> Result<Self, vk::Result> {
        let mut p = Self {
            device: d.clone(),
            targets: vec![],
            clear_pass: vk::RenderPass::null(),
            load_pass: vk::RenderPass::null(),
            pipeline: vk::Pipeline::null(),
            composite: vk::Pipeline::null(),
            additive_pipeline: vk::Pipeline::null(),
            additive,
            layout: vk::PipelineLayout::null(),
            set_layout: vk::DescriptorSetLayout::null(),
            pool: vk::DescriptorPool::null(),
            sets: vec![],
            sampler: vk::Sampler::null(),
            shaders: vec![],
        };
        let format = vk::Format::R8G8B8A8_UNORM;
        let features = instance
            .get_physical_device_format_properties(gpu, format)
            .optimal_tiling_features;
        if !features.contains(
            vk::FormatFeatureFlags::COLOR_ATTACHMENT
                | vk::FormatFeatureFlags::SAMPLED_IMAGE_FILTER_LINEAR,
        ) {
            return Err(vk::Result::ERROR_FORMAT_NOT_SUPPORTED);
        }
        let reference = [vk::AttachmentReference::default()
            .attachment(0)
            .layout(vk::ImageLayout::COLOR_ATTACHMENT_OPTIMAL)];
        let subpasses = [vk::SubpassDescription::default()
            .pipeline_bind_point(vk::PipelineBindPoint::GRAPHICS)
            .color_attachments(&reference)];
        let deps = [
            vk::SubpassDependency::default()
                .src_subpass(vk::SUBPASS_EXTERNAL)
                .dst_subpass(0)
                .src_stage_mask(
                    vk::PipelineStageFlags::FRAGMENT_SHADER
                        | vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT,
                )
                .dst_stage_mask(vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT)
                .src_access_mask(
                    vk::AccessFlags::SHADER_READ | vk::AccessFlags::COLOR_ATTACHMENT_WRITE,
                )
                .dst_access_mask(
                    vk::AccessFlags::COLOR_ATTACHMENT_READ
                        | vk::AccessFlags::COLOR_ATTACHMENT_WRITE,
                ),
            vk::SubpassDependency::default()
                .src_subpass(0)
                .dst_subpass(vk::SUBPASS_EXTERNAL)
                .src_stage_mask(vk::PipelineStageFlags::COLOR_ATTACHMENT_OUTPUT)
                .dst_stage_mask(vk::PipelineStageFlags::FRAGMENT_SHADER)
                .src_access_mask(vk::AccessFlags::COLOR_ATTACHMENT_WRITE)
                .dst_access_mask(vk::AccessFlags::SHADER_READ),
        ];
        for load in [false, true] {
            let attachments = [vk::AttachmentDescription::default()
                .format(format)
                .samples(vk::SampleCountFlags::TYPE_1)
                .load_op(if load {
                    vk::AttachmentLoadOp::LOAD
                } else {
                    vk::AttachmentLoadOp::CLEAR
                })
                .store_op(vk::AttachmentStoreOp::STORE)
                .initial_layout(if load {
                    vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL
                } else {
                    vk::ImageLayout::UNDEFINED
                })
                .final_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)];
            let pass = d.create_render_pass(
                &vk::RenderPassCreateInfo::default()
                    .attachments(&attachments)
                    .subpasses(&subpasses)
                    .dependencies(&deps),
                None,
            )?;
            if load {
                p.load_pass = pass;
            } else {
                p.clear_pass = pass;
            }
        }
        let props = instance.get_physical_device_memory_properties(gpu);
        let mut sizes = vec![512; 3];
        if additive {
            sizes.extend([256, 128, 128, 64, 64, 32, 32, 16, 16, 8, 8]);
        }
        for size in sizes {
            p.targets.push(Target::default());
            let t = p.targets.last_mut().unwrap();
            t.size = size;
            t.image = d.create_image(
                &vk::ImageCreateInfo::default()
                    .image_type(vk::ImageType::TYPE_2D)
                    .format(format)
                    .extent(vk::Extent3D {
                        width: size,
                        height: size,
                        depth: 1,
                    })
                    .mip_levels(1)
                    .array_layers(1)
                    .samples(vk::SampleCountFlags::TYPE_1)
                    .tiling(vk::ImageTiling::OPTIMAL)
                    .usage(vk::ImageUsageFlags::COLOR_ATTACHMENT | vk::ImageUsageFlags::SAMPLED),
                None,
            )?;
            let req = d.get_image_memory_requirements(t.image);
            let ty = (0..props.memory_type_count)
                .find(|&i| {
                    req.memory_type_bits & (1 << i) != 0
                        && props.memory_types[i as usize]
                            .property_flags
                            .contains(vk::MemoryPropertyFlags::DEVICE_LOCAL)
                })
                .ok_or(vk::Result::ERROR_FEATURE_NOT_PRESENT)?;
            t.memory = d.allocate_memory(
                &vk::MemoryAllocateInfo::default()
                    .allocation_size(req.size)
                    .memory_type_index(ty),
                None,
            )?;
            d.bind_image_memory(t.image, t.memory, 0)?;
            t.view = d.create_image_view(
                &vk::ImageViewCreateInfo::default()
                    .image(t.image)
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
            t.framebuffer = d.create_framebuffer(
                &vk::FramebufferCreateInfo::default()
                    .render_pass(p.clear_pass)
                    .attachments(&[t.view])
                    .width(size)
                    .height(size)
                    .layers(1),
                None,
            )?;
        }
        p.sampler = d.create_sampler(
            &vk::SamplerCreateInfo::default()
                .mag_filter(vk::Filter::LINEAR)
                .min_filter(vk::Filter::LINEAR)
                .address_mode_u(vk::SamplerAddressMode::CLAMP_TO_EDGE)
                .address_mode_v(vk::SamplerAddressMode::CLAMP_TO_EDGE),
            None,
        )?;
        let bindings: Vec<_> = (0..2)
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
        let mut views: Vec<_> = std::iter::once(source)
            .chain(p.targets.iter().map(|t| t.view))
            .map(|v| [v, v])
            .collect();
        if additive {
            for (a, b) in [(12, 10), (8, 6), (4, 3)] {
                views.push([p.targets[a].view, p.targets[b].view]);
            }
        }
        let count = views.len() as u32;
        p.pool = d.create_descriptor_pool(
            &vk::DescriptorPoolCreateInfo::default()
                .max_sets(count)
                .pool_sizes(&[vk::DescriptorPoolSize::default()
                    .ty(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                    .descriptor_count(count * 2)]),
            None,
        )?;
        p.sets = d.allocate_descriptor_sets(
            &vk::DescriptorSetAllocateInfo::default()
                .descriptor_pool(p.pool)
                .set_layouts(&vec![p.set_layout; count as usize]),
        )?;
        for (i, pair) in views.iter().enumerate() {
            for (binding, view) in pair.iter().enumerate() {
                let info = [vk::DescriptorImageInfo::default()
                    .sampler(p.sampler)
                    .image_view(*view)
                    .image_layout(vk::ImageLayout::SHADER_READ_ONLY_OPTIMAL)];
                d.update_descriptor_sets(
                    &[vk::WriteDescriptorSet::default()
                        .dst_set(p.sets[i])
                        .dst_binding(binding as u32)
                        .descriptor_type(vk::DescriptorType::COMBINED_IMAGE_SAMPLER)
                        .image_info(&info)],
                    &[],
                );
            }
        }
        p.layout = d.create_pipeline_layout(
            &vk::PipelineLayoutCreateInfo::default()
                .set_layouts(&[p.set_layout])
                .push_constant_ranges(&[vk::PushConstantRange::default()
                    .stage_flags(vk::ShaderStageFlags::FRAGMENT)
                    .size(32)]),
            None,
        )?;
        for bytes in [
            include_bytes!(concat!(env!("OUT_DIR"), "/menu_blur.vert.spv")).as_slice(),
            include_bytes!(concat!(env!("OUT_DIR"), "/menu_blur.frag.spv")).as_slice(),
        ] {
            let code = ash::util::read_spv(&mut Cursor::new(bytes))
                .map_err(|_| vk::Result::ERROR_INITIALIZATION_FAILED)?;
            p.shaders.push(
                d.create_shader_module(&vk::ShaderModuleCreateInfo::default().code(&code), None)?,
            );
        }
        p.pipeline = p.create_pipeline(p.clear_pass, 0)?;
        p.composite = p.create_pipeline(main_pass, 1)?;
        if additive {
            p.additive_pipeline = p.create_pipeline(main_pass, 2)?;
        }
        Ok(p)
    }
    unsafe fn create_pipeline(
        &self,
        pass: vk::RenderPass,
        composite: u32,
    ) -> Result<vk::Pipeline, vk::Result> {
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
        let depth = vk::PipelineDepthStencilStateCreateInfo::default();
        let attachment = [vk::PipelineColorBlendAttachmentState::default()
            .blend_enable(composite != 0)
            .src_color_blend_factor(if composite == 2 {
                vk::BlendFactor::ONE
            } else {
                vk::BlendFactor::SRC_ALPHA
            })
            .dst_color_blend_factor(if composite == 2 {
                vk::BlendFactor::ONE
            } else {
                vk::BlendFactor::ONE_MINUS_SRC_ALPHA
            })
            .color_blend_op(vk::BlendOp::ADD)
            .src_alpha_blend_factor(vk::BlendFactor::ONE)
            .dst_alpha_blend_factor(vk::BlendFactor::ZERO)
            .alpha_blend_op(vk::BlendOp::ADD)
            .color_write_mask(if composite != 0 {
                vk::ColorComponentFlags::R | vk::ColorComponentFlags::G | vk::ColorComponentFlags::B
            } else {
                vk::ColorComponentFlags::RGBA
            })];
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
            .depth_stencil_state(&depth)
            .color_blend_state(&blend)
            .dynamic_state(&dynamic)
            .layout(self.layout)
            .render_pass(pass);
        match self
            .device
            .create_graphics_pipelines(vk::PipelineCache::null(), &[info], None)
        {
            Ok(v) => Ok(v[0]),
            Err((partial, e)) => {
                for p in partial {
                    self.device.destroy_pipeline(p, None);
                }
                Err(e)
            }
        }
    }
    unsafe fn quad(
        &self,
        cmd: vk::CommandBuffer,
        set: usize,
        pipeline: vk::Pipeline,
        viewport: [f32; 4],
        parameters: [f32; 8],
    ) {
        let d = &self.device;
        d.cmd_set_viewport(
            cmd,
            0,
            &[vk::Viewport {
                x: viewport[0],
                y: viewport[1],
                width: viewport[2],
                height: viewport[3],
                min_depth: 0.,
                max_depth: 1.,
            }],
        );
        d.cmd_bind_pipeline(cmd, vk::PipelineBindPoint::GRAPHICS, pipeline);
        d.cmd_bind_descriptor_sets(
            cmd,
            vk::PipelineBindPoint::GRAPHICS,
            self.layout,
            0,
            &[self.sets[set]],
            &[],
        );
        let bytes: Vec<u8> = parameters.iter().flat_map(|v| v.to_ne_bytes()).collect();
        d.cmd_push_constants(cmd, self.layout, vk::ShaderStageFlags::FRAGMENT, 0, &bytes);
        d.cmd_draw(cmd, 3, 1, 0, 0);
    }
    pub unsafe fn build(&self, cmd: vk::CommandBuffer, source_rect: [f32; 4]) {
        let d = &self.device;
        // S is the scene copy, A preserves its current-frame border, B starts black.
        let mut passes = vec![
            (0, 0, 512, 1., 1., 3., false),
            (1, 1, 512, 1., 256. / 255., 0., false),
            (2, 2, 256, 1., 256. / 255., 0., false),
            (1, 3, 128, 0.5, 1., 1., true),
            (2, 2, 256, 0.25, 1., 1., true),
        ];
        if self.additive {
            passes.push((3, 1, 256, 1., 1., 4., false));
            let mut previous = 3;
            for (target, size) in [(4, 128), (6, 64), (8, 32), (10, 16), (12, 8)] {
                passes.push((target, previous + 1, size, 1., 256. / 255., 0., false));
                passes.push((target + 1, target + 1, size, 1., 1., 5., false));
                passes.push((target, target + 2, size, 1., 1., 6., false));
                previous = target;
            }
        }
        for (target, source, size, span, gain, mode, load) in passes {
            let rect = vk::Rect2D::default().extent(vk::Extent2D {
                width: self.targets[target].size,
                height: self.targets[target].size,
            });
            let clear = [vk::ClearValue {
                color: vk::ClearColorValue { float32: [0.; 4] },
            }];
            d.cmd_begin_render_pass(
                cmd,
                &vk::RenderPassBeginInfo::default()
                    .render_pass(if load {
                        self.load_pass
                    } else {
                        self.clear_pass
                    })
                    .framebuffer(self.targets[target].framebuffer)
                    .render_area(rect)
                    .clear_values(&clear),
                vk::SubpassContents::INLINE,
            );
            d.cmd_set_scissor(cmd, 0, &[rect]);
            let r = if source == 0 {
                source_rect
            } else {
                [0., 0., 1., 1.]
            };
            self.quad(
                cmd,
                source,
                self.pipeline,
                [0., 0., size as f32, size as f32],
                [span, gain, mode, 0., r[0], r[1], r[2], r[3]],
            );
            d.cmd_end_render_pass(cmd);
        }
    }
    pub unsafe fn additive_composite(
        &self,
        cmd: vk::CommandBuffer,
        viewport: [f32; 4],
        extent: vk::Extent2D,
    ) {
        if !self.additive {
            return;
        }
        self.device
            .cmd_set_scissor(cmd, 0, &[vk::Rect2D::default().extent(extent)]);
        for set in 15..18 {
            self.quad(
                cmd,
                set,
                self.additive_pipeline,
                viewport,
                [1., 1., 7., 0., 0., 0., 1., 1.],
            );
        }
    }
    pub unsafe fn composite(
        &self,
        cmd: vk::CommandBuffer,
        viewport: [f32; 4],
        extent: vk::Extent2D,
    ) {
        self.device
            .cmd_set_scissor(cmd, 0, &[vk::Rect2D::default().extent(extent)]);
        self.quad(
            cmd,
            3,
            self.composite,
            viewport,
            [0.5, 1., 2., 0., 0., 0., 1., 1.],
        );
    }
}
impl Drop for MenuBlur {
    fn drop(&mut self) {
        unsafe {
            let d = &self.device;
            d.destroy_pipeline(self.pipeline, None);
            d.destroy_pipeline(self.composite, None);
            d.destroy_pipeline(self.additive_pipeline, None);
            d.destroy_pipeline_layout(self.layout, None);
            for s in self.shaders.drain(..) {
                d.destroy_shader_module(s, None);
            }
            d.destroy_descriptor_pool(self.pool, None);
            d.destroy_descriptor_set_layout(self.set_layout, None);
            d.destroy_sampler(self.sampler, None);
            for t in self.targets.drain(..) {
                d.destroy_framebuffer(t.framebuffer, None);
                d.destroy_image_view(t.view, None);
                d.destroy_image(t.image, None);
                d.free_memory(t.memory, None);
            }
            d.destroy_render_pass(self.clear_pass, None);
            d.destroy_render_pass(self.load_pass, None);
        }
    }
}
