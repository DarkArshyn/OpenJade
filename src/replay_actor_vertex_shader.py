"""Replay captured vertex-shader arithmetic; original shader text remains external."""
from pathlib import Path
import re, json, hashlib, struct
import numpy as np


def disassemble(code):
    """Use the local Direct3D compiler to inspect captured bytecode in memory."""
    import ctypes as ctypes
    blob = ctypes.c_void_p()
    result = ctypes.WinDLL('d3dcompiler_47').D3DDisassemble(code, len(code), 0, None, ctypes.byref(blob))
    if result != 0:
        raise ValueError(f'D3DDisassemble failed: {result}')
    table = ctypes.cast(blob, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    try:
        pointer = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p)(table[3])(blob)
        return ctypes.string_at(pointer).decode('ascii')
    finally:
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(table[2])(blob)


def program(text, inputs, constants):
    registers = {key: value.copy() for key, value in inputs.items()}
    registers.update({f'c{i}': value.copy() for i, value in enumerate(constants)})
    registers['a0'] = np.zeros(4)
    def read(token):
        sign = -1 if token.startswith('-') else 1
        token = token.lstrip('-')
        token = re.sub(r'c(\d+)\[a0.x\]', lambda m: 'c'+str(int(m[1])+int(registers['a0'][0])), token)
        parts = token.split('.')
        value = registers[parts[0]]
        if len(parts) == 2:
            swizzle = parts[1]
            swizzle += swizzle[-1]*(4-len(swizzle))
            value = value[['xyzw'.index(c) for c in swizzle]]
        return sign*value
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('//', 'vs_', 'ps_', 'dcl_')):
            continue
        op, rest = line.split(None, 1)
        tokens = [p.strip() for p in rest.split(',')]
        if op == 'tex':
            assert tokens[0] in registers, 'Texture samples must be supplied externally'
            continue
        modifiers = op.split('_')
        op = modifiers[0]
        dst = tokens[0].split('.')
        src = [read(t) for t in tokens[1:]]
        if op == 'mov': out = src[0]
        elif op == 'add': out = src[0]+src[1]
        elif op == 'mul': out = src[0]*src[1]
        elif op == 'mad': out = src[0]*src[1]+src[2]
        elif op == 'lrp': out = src[0]*src[1]+(1-src[0])*src[2]
        elif op in ('dp3', 'dp4'):
            size = int(op[-1]); out = np.repeat(np.dot(src[0][:size], src[1][:size]), 4)
        elif op == 'rsq': out = np.repeat(1/np.sqrt(abs(src[0][0])), 4)
        elif op == 'rcp': out = np.repeat(1/src[0][0], 4)
        elif op == 'max': out = np.maximum(src[0], src[1])
        elif op == 'min': out = np.minimum(src[0], src[1])
        elif op == 'sge': out = (src[0] >= src[1]).astype(float)
        elif op in ('m4x4', 'm3x3'):
            size = int(op[1]); first = int(tokens[2][1:]); out = np.zeros(4)
            out[:size] = constants[first:first+size, :size]@src[0][:size]
        else: raise AssertionError('Unsupported opcode '+op)
        if 'x2' in modifiers: out = out*2
        if 'sat' in modifiers: out = np.clip(out, 0, 1)
        registers.setdefault(dst[0], np.zeros(4))
        mask = dst[1] if len(dst) > 1 else 'xyzw'
        for channel in mask:
            i = 'xyzw'.index(channel); registers[dst[0]][i] = out[i]
    return registers


def formula(inputs, c):
    position, normal = inputs['v0'].copy(), inputs['v2'][:3].copy()
    if 'v1' in inputs:
        bone = sum(inputs['v1'][j]*c[42+int(inputs['v7'][j]):45+int(inputs['v7'][j])] for j in range(3))
        position = np.r_[bone@position, 1.]
        normal = bone[:, :3]@normal
    view = c[4:8]@position
    normal = c[8:11, :3]@normal
    normal /= np.linalg.norm(normal)
    terms = [c[25, :3], max(float(normal@c[27, :3]), 0)*c[28, :3]]
    for p, attenuation, color in [(30, 33, 32), (34, 37, 36)]:
        delta = c[p, :3]-view[:3]; distance = np.linalg.norm(delta)
        factor = np.clip((c[attenuation, 0]-distance)*c[attenuation, 1], 0, 1)
        terms.append(np.clip(normal@(delta/distance), 0, 1)*factor*c[color, :3])
    terms.append(max(float(normal@c[39, :3]), 0)*c[40, :3])
    return np.sum(terms, axis=0), np.array(terms)


def replay(folder):
    shaders = {}
    for path in folder.glob('*.vs'):
        code = path.read_bytes(); digest = hashlib.sha256(code).hexdigest()
        if digest not in shaders: shaders[digest] = disassemble(code)
    results=[]
    for meta in sorted(folder.glob(f'{folder.name}-draw-*.txt')):
        lines=meta.read_text().splitlines(); shader=shaders[hashlib.sha256(meta.with_suffix('.vs').read_bytes()).hexdigest()]
        if 'mov oD0' not in shader: continue
        h=lines[0].split();count=int(h[3]);start=int(h[5]);base=int(h[7]);indexed=int(h[11])
        assert indexed == 1
        decl=[list(map(int,line.split()[1:])) for line in lines if line.startswith('decl ') and not line.startswith('decl 255')]
        stream=next(line.split() for line in lines if line.startswith('stream 0 '));offset=int(stream[3]);stride=int(stream[5])
        raw=meta.with_suffix('.stream0').read_bytes();c=np.fromfile(meta.with_suffix('.constants'),'<f4').astype(float).reshape(256,4)
        assert np.array_equal(c[16,:2],[0,1])
        ids=np.fromfile(meta.with_suffix('.indices'),'<u2')[start:start+count*3].astype(int)+base
        assert len(ids)==count*3
        maximum=0.;terms_all=[]
        for vertex in np.unique(ids):
            inputs={}
            for stream,field,type_,method,usage,index in decl:
                assert stream==0 and method==0 and index==0
                formats={1:('<2f',2),2:('<3f',3),7:('<4h',4)}
                fmt,n=formats[type_];value=np.array([0.,0.,0.,1.]);value[:n]=struct.unpack_from(fmt,raw,offset+int(vertex)*stride+field)
                inputs[{0:'v0',3:'v2',5:'v9',1:'v1',2:'v7'}[usage]]=value
            interpreted=program(shader,inputs,c)['oD0'][:3]
            expected,terms=formula(inputs,c)
            maximum=max(maximum,float(np.max(np.abs(interpreted-expected))))
            terms_all.append(terms)
        assert maximum<1e-10
        results.append(dict(draw=meta.stem,receiver=h[1],vertices=len(np.unique(ids)),triangles=count,
                            max_error=maximum,term_max=np.max(terms_all,axis=(0,2)).tolist(),
                            shader_sha256=hashlib.sha256(meta.with_suffix('.vs').read_bytes()).hexdigest()))
    return dict(draws=len(results),vertices=sum(row['vertices'] for row in results),max_error=max(row['max_error'] for row in results),results=results)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('capture',type=Path)
    print(json.dumps(replay(parser.parse_args().capture),indent=2))
