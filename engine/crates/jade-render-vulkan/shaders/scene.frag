#version 450
layout(set=0,binding=0) uniform sampler2DArray nearestTextures;
layout(set=0,binding=1) uniform sampler2DArray linearTextures;
layout(set=0,binding=2) uniform sampler2DArray fogTextures;
layout(set=0,binding=3) uniform sampler2DArray reflectionTexture;
layout(location=5) in vec2 reflectionUV;
layout(location=0) in vec2 uv;
layout(location=1) in vec3 color;
layout(location=2) flat in float layer;
layout(location=3) in float fogAmount;
layout(location=4) in float diffuseAlpha;
layout(location=0) out vec4 output_color;
layout(push_constant) uniform Material {
    layout(offset=80) vec4 uvTransform;
    vec4 shading; // alpha, RGB gain, alpha cutoff, sampler selector
    float fogMode;
    float reflectionR; float reflectionG; float reflectionB;
} material;
void main() {
    vec3 coords=vec3(uv*material.uvTransform.xy+material.uvTransform.zw,0.0);
    vec4 texel;
    if(material.shading.w<0.5) texel=texture(nearestTextures,coords);
    else if(material.shading.w<1.5) texel=texture(linearTextures,coords);
    else texel=texture(fogTextures,coords);
    float alpha=texel.a*material.shading.x;
    bool reflective = material.fogMode >= 8.0;
    float mode = material.fogMode - (reflective ? 8.0 : 0.0);
    bool perVertexAlpha = mode >= 4.0;
    if(perVertexAlpha) alpha *= diffuseAlpha;
    if(perVertexAlpha ? alpha <= material.shading.z : alpha < material.shading.z) discard;
    float fogMode = perVertexAlpha ? mode-4.0 : mode;
    vec3 rgb=clamp(texel.rgb*color*material.shading.y,0.0,1.0);
    if(reflective) {
        vec4 reflection = textureLod(reflectionTexture, vec3(reflectionUV,0.0),0.0);
        vec3 tint = vec3(material.reflectionR,material.reflectionG,material.reflectionB);
        rgb = clamp(2.0*((1.0-texel.a)*texel.rgb*color + texel.a*reflection.rgb*tint),0.0,1.0);
        alpha = (1.0-texel.a)*texel.a + texel.a*reflection.a;
    }
    if(fogMode>0.5){
        float amount=fogMode<1.5 ? fogAmount : 1.0-fogAmount;
        rgb=mix(rgb,vec3(52,78,95)/255.0,amount);
    }
    output_color=vec4(rgb,alpha);
}
