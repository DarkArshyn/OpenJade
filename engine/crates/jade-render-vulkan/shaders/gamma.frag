#version 450
layout(input_attachment_index=0,set=0,binding=0) uniform subpassInput composed;
layout(std140,set=0,binding=1) uniform Gamma { vec4 ramp[256]; vec4 options; } data;
layout(location=0) out vec4 output_color;
vec3 encode(vec3 c) {return mix(12.92*c,1.055*pow(max(c,vec3(0.0)),vec3(1.0/2.4))-0.055,greaterThan(c,vec3(0.0031308)));}
vec3 decode(vec3 c) {return mix(c/12.92,pow((c+0.055)/1.055,vec3(2.4)),greaterThan(c,vec3(0.04045)));}
float lookup(float c) {float x=clamp(c,0.0,1.0)*255.0;int i=int(floor(x));return mix(data.ramp[i].x,data.ramp[min(i+1,255)].x,fract(x));}
void main() {
    vec4 color=subpassLoad(composed);
    if(data.options.x>0.5) {
        vec3 stored=data.options.y>0.5?encode(color.rgb):color.rgb;
        stored=vec3(lookup(stored.r),lookup(stored.g),lookup(stored.b));
        color.rgb=data.options.y>0.5?decode(stored):stored;
    }
    output_color=color;
}
