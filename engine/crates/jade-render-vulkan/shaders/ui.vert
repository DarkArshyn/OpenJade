#version 450
layout(location=0) in vec3 position;
layout(location=1) in vec2 uv_in;
layout(location=2) in vec3 color_in;
layout(location=3) in float layer_in;
layout(location=4) in float alpha_in;
layout(location=4) out float diffuseAlpha;
layout(location=0) out vec2 uv;
layout(location=1) out vec3 color;
layout(location=2) flat out float layer;
layout(location=3) out float fogAmount;
void main(){diffuseAlpha=alpha_in;fogAmount=0.0;gl_Position=vec4(position.xy,0,1);uv=uv_in;color=color_in;layer=layer_in;}
