"""Export the measured receiver-to-source-bone mappings, not vertex influences."""
import struct
from prince_animation import Skeleton


def encode(resources, report):
    skeleton=Skeleton(resources)
    # Verified by same-session owner bindings and 275 captured palettes per receiver.
    mapping={0x3F000E05:0x130035BE,0x13008483:0x130035C0}
    root_meshes={0x33001050,0x057CC7F4,0x13008426,0x13008425,0x1300842C,
                 0x13008427,0x1300842A,0x13008428,0x1300842B}
    origins=[]
    for draw in report['draws']:
        mesh=int(draw['mesh'],16);count=draw['triangles']*3
        if not isinstance(count,int) or not 0<count<=1000000:
            raise ValueError('Invalid receiver vertex count')
        if mesh in mapping:bone=skeleton.index[mapping[mesh]]
        elif mesh in root_meshes:bone=0xffffffff
        else:raise ValueError('Unverified lighting receiver')
        origins.extend([bone]*count)
    if len(origins)!=report['triangles']*3:raise ValueError('Receiver count mismatch')
    return b'OJAORG01'+struct.pack('<I',len(origins))+struct.pack('<'+'I'*len(origins),*origins)
