"""Build sparse OJSCN005 palm controls from frozen GAOs and local mesh coordinates."""
import struct
import numpy as np
from inspect_menu_palms import inspect
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
    for palm in palms:
        matrix = np.frombuffer(payload(palm['key']), dtype='<f4', count=16,
                               offset=palm['matrix_offset']).astype(float).reshape(4, 4)
        local = primary_mesh(payload(palm['mesh']))[0][:, :3]
        basis = matrix[:3, :3]
        world = local @ basis + matrix[3, :3]
        coordinates = dict(zip(map(tuple, world), local))
        component = palm['component']
        quarter = component['flags'] == 7
        axes = basis[[1, 2] if quarter else [0, 0]] * component['amplitude']
        controls[palm['name']] = (coordinates, component, quarter, axes.ravel())
    counts = {}
    for draw, entry in zip(draws, audit, strict=True):
        name = entry['object']
        if name not in controls:
            continue
        coords, component, quarter, axes = controls[name]
        start, count = draw[:2]
        for index in range(start, start + count):
            xyz = coords[tuple(vertices[index][:3])]
            angles = xyz[[0, 0] if quarter else [1, 2]] * component['spatial_factor']
            blob.extend(struct.pack('<II9f', index, quarter, *angles,
                                    component['phase_rate_factor'], *axes))
        counts[name] = counts.get(name, 0) + count
    if counts.keys() != controls.keys():
        raise ValueError('Incomplete frozen palm geometry')
    blob.extend(struct.pack('<I', sum(counts.values())))
    return counts
