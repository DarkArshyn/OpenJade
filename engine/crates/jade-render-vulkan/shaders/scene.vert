#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec2 uv_in;
layout(location=2) in vec3 color_in;
layout(location=3) in float layer_in;
layout(location=0) out vec2 uv;
layout(location=1) out vec3 color;
layout(location=2) flat out float layer;
layout(push_constant) uniform Camera { vec4 eye; vec4 right; vec4 up; vec4 forward; vec4 projection; } camera;
void main() {
    vec3 delta=position-camera.eye.xyz;
    float depth=dot(delta,camera.forward.xyz);
    float focal=camera.projection.x, aspect=camera.projection.y;
    float nearZ=camera.projection.z, farZ=camera.projection.w;
    gl_Position=vec4(dot(delta,camera.right.xyz)*focal/aspect,
                     -dot(delta,camera.up.xyz)*focal,
                     farZ*depth/(farZ-nearZ)-farZ*nearZ/(farZ-nearZ),depth);
    uv=uv_in; color=color_in; layer=layer_in;
}
