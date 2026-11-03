#version 450
layout(location=0) in vec2 uv;
layout(location=0) out vec4 outputColor;
layout(binding=0) uniform sampler2D sourceImage;
layout(binding=1) uniform sampler2D secondImage;
layout(push_constant) uniform Parameters { vec4 control; vec4 sourceRect; } p;
void main() {
    vec2 tc=p.sourceRect.xy+uv*p.sourceRect.zw*p.control.x;
    vec4 texel=texture(sourceImage,tc);
    if(p.control.z==3.0) { outputColor=texel; return; }
    if(p.control.z==4.0) { outputColor=vec4(min(texel.rgb*(256.0/255.0),vec3(1))*texel.a,1); return; }
    if(p.control.z==7.0) { outputColor=vec4((texel.rgb+texture(secondImage,tc).rgb)*(256.0/255.0),1); return; }
    if(p.control.z==5.0 || p.control.z==6.0) {
        vec2 delta=(p.control.z==5.0 ? vec2(1,0):vec2(0,1))/vec2(textureSize(sourceImage,0));
        outputColor=vec4((texture(sourceImage,tc-delta).rgb+texel.rgb+texture(sourceImage,tc+delta).rgb)*0.365234405,1); return;
    }
    vec3 rgb;
    if(p.control.z==1.0) {
        rgb=(texture(sourceImage,tc+vec2(-1,-1)/512.0).rgb
            +texture(sourceImage,tc+vec2(1,0)/512.0).rgb
            +texture(sourceImage,tc+vec2(0,1)/512.0).rgb)*0.333332986;
    } else {
        rgb=texture(sourceImage,tc).rgb*p.control.y;
    }
    outputColor=vec4(rgb,p.control.z==2.0 ? 104.0/255.0 : 1.0);
}
