#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec2 uv_in;
layout(location=2) in vec3 color_in;
layout(location=3) in float layer_in;
layout(location=0) out vec2 uv;
layout(location=1) out vec3 color;
layout(location=2) flat out float layer;
void main(){gl_Position=vec4(position.xy,0,1);uv=uv_in;color=color_in;layer=layer_in;}
