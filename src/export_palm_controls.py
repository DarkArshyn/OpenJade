"""Build sparse OJSCN005 palm controls from frozen GAOs and local mesh coordinates."""
import struct
import numpy as np
from inspect_menu_palms import inspect
from inspect_menu_scene_links import static_links
from menu_fog_state import transform_fog_points
from probe_menu3d import records
from menu_primary_geometry import primary_mesh


def append_palms(blob, source, vertices, draws, audit):
    raw = source.read_bytes()
    palms = [row for row in inspect(raw)['palms'] if row['component']]
    inventory = {row['key']: row for row in records(raw)}
    def payload(key):
        entry = inventory[key]
        return raw[entry['offset'] + 12:entry['end']]

    controls = {}
    vegetation = {"0x30000CBB":15, "0x30000CC6":7, "0x30000CCF":12, "0x30000CCE":2}
    drawn = {entry["object"] for entry in audit}
    for key,expected in vegetation.items():
        obj=payload(key)
        link=static_links(obj)
        if link["name"] not in drawn:
            continue
        kind,header,version,flags,phase,amp,space,rate,group,end=struct.unpack_from("<4I4f2I",obj,len(obj)-40)
        if (kind,header,version,flags,phase,group,end)!=(1,0,25,expected,0.,0xffffffff,0xffffffff):
            raise ValueError("Unsupported vegetation modifier for "+link["name"])
        palms.append(dict(key=key,component=dict(flags=flags,amplitude=amp,spatial_factor=space,phase_rate_factor=rate),**link))

    for palm in palms:
        matrix = np.frombuffer(payload(palm['key']), dtype='<f4', count=16,
                               offset=palm['matrix_offset']).astype(float).reshape(4, 4)
        local = primary_mesh(payload(palm['mesh']))[0][:, :3]
        basis = matrix[:3, :3].copy()
        if palm['key']=="0x30000CCE":
            world=transform_fog_points(local,matrix)
            basis *= matrix[:3,3,None]
        else:
            world = local @ basis + matrix[3, :3]
        coords=dict(zip(map(tuple,world),local))
        controls[palm['name']]=(coords,palm['component'],basis)
    counts = {}
    for draw, entry in zip(draws, audit, strict=True):
        name = entry['object']
        if name not in controls:
            continue
        coords, component, basis = controls[name]
        flags=component["flags"]
        directions={7:[1,2],2:[0,2],15:[0,0],12:[2,2]}[flags]
        drivers={7:[0,0],2:[1,1],15:[1,2],12:[0,1]}[flags]
        quarter=flags in (7,2)
        start, count = draw[:2]
        for index in range(start, start + count):
            xyz = coords[tuple(vertices[index][:3])]
            angles=xyz[drivers]*component['spatial_factor']
            axes=basis[directions]*component['amplitude']
            if flags==12:
                # Two spatial waves modulate the amplitude of one temporal wave.
                indices=np.rint(angles*float(np.float32(1024/(2*np.pi)))).astype(int)%1024
                waves=np.sin(indices*float(np.float32(2*np.pi/1024))).astype(np.float32)
                axes[0]*=2*float(waves.sum())
                axes[1]=0
                angles=[0.,0.]
            axes=axes.ravel()
            blob.extend(struct.pack('<II9f', index, quarter, *angles,
                                    component['phase_rate_factor'], *axes))
        counts[name] = counts.get(name, 0) + count
    if counts.keys() != controls.keys():
        raise ValueError('Incomplete frozen palm geometry')
    blob.extend(struct.pack('<I', sum(counts.values())))
    return counts
