#version 450
layout(location=0) out vec2 uv;
const vec2 positions[6] = vec2[](vec2(-1,-1),vec2(1,-1),vec2(1,1),vec2(-1,-1),vec2(1,1),vec2(-1,1));
void main() { vec2 p=positions[gl_VertexIndex]; uv=(p+1.0)*0.5; gl_Position=vec4(p,0,1); }
