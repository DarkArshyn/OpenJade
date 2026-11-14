"""Independent, bounded evaluation of the observed TSoT Prince body tracks.

No historical engine source is used. Untracked secondary joints retain their
resource-local transforms; this does not reproduce their procedural controllers.
"""
import math
import struct
import numpy as np
from sample_camera02_animation import native_slerp, quaternion_matrix


def decode_tracks(data):
    if len(data) < 4:
        raise ValueError('Truncated controller')
    count, flags = struct.unpack_from('<2H', data)
    if flags != 2 or not 0 < count <= 160:
        raise ValueError('Unsupported controller header')
    pos = 4
    tracks = []
    def take(fmt):
        nonlocal pos
        size = struct.calcsize(fmt)
        if pos + size > len(data):
            raise ValueError('Truncated track')
        values = struct.unpack_from(fmt, data, pos)
        pos += size
        return values
    for _ in range(count):
        start = pos
        flags, target, allocation, n = take('<HHII')
        if not 0 < n <= 10000 or not flags & 0x8000:
            raise ValueError('Unsupported track encoding')
        keys = []
        ticks = 0
        for j in range(n):
            duration = take('<B' if flags & 0x200 else '<H')[0]
            if j == 0:
                event, expanded, payload = take('<3H')
                if (expanded, payload) not in ((12, 0x1010), (16, 1)) or event & 0xfff8 != 0x80:
                    raise ValueError('Unsupported transform payload')
                if allocation != n * expanded:
                    raise ValueError('Expanded allocation mismatch')
            values = take('<4h' if payload == 0x1010 else '<3f')
            if not all(math.isfinite(x) for x in values) or (duration == 0 and j != n - 1):
                raise ValueError('Invalid transform key')
            keys.append(dict(tick=ticks, duration=duration, values=list(values)))
            ticks += duration
        tracks.append(dict(offset=start, end=pos, flags=flags, target=target,
                           kind='rotation' if payload == 0x1010 else 'translation',
                           keys=keys, duration_ticks=ticks))
    if pos != len(data):
        raise ValueError('Unparsed controller tail')
    return tracks


def sample(track, tick):
    if not math.isfinite(tick) or tick < 0:
        raise ValueError('Invalid track time')
    keys = track['keys']
    rotation = track['kind'] == 'rotation'
    def value(k):
        return np.asarray(k['values'], float) / (32768 if rotation else 1)
    if tick >= keys[-1]['tick']:
        return value(keys[-1])
    i = max(i for i, k in enumerate(keys) if k['tick'] <= tick)
    a, b = value(keys[i]), value(keys[i + 1])
    phase = (tick - keys[i]['tick']) / keys[i]['duration']
    return native_slerp(a, b, phase) if rotation else a + (b - a) * phase


def node(resources, key):
    d = resources.get(key)
    if len(d) < 20 or d[:4] != b'.gao':
        raise ValueError('Invalid skeleton object')
    flags, n = struct.unpack_from('<2I', d, 12)
    if not 1 <= n <= 1024 or len(d) < n + 122:
        raise ValueError('Invalid skeleton object extent')
    matrix = np.frombuffer(d, '<f4', count=16, offset=n + 30).astype(float).reshape(4, 4)
    # The last column stores native flags/scales, not affine coordinates.
    if not np.isfinite(matrix[:, :3]).all() or np.any(matrix[:3, 3] != 0):
        raise ValueError('Unsupported scaled bone')
    matrix[:, 3] = [0, 0, 0, 1]
    at = n + 122 + (24 if flags & 0x80000 else 0)
    if flags & 0x4000:
        at += 38
        if at + 4 > len(d):raise ValueError('Truncated object blocks')
        blocks = struct.unpack_from('<I', d, at)[0]
        at += 4
        if blocks > 256:raise ValueError('Too many object blocks')
        for _ in range(blocks):
            if at + 4 > len(d):raise ValueError('Truncated object block')
            size = struct.unpack_from('<I', d, at)[0]
            at += 4 + size
            if at > len(d):raise ValueError('Truncated object block payload')
    if flags & 0x400000:
        if at + 4 > len(d):raise ValueError('Missing bone parent')
        parent = struct.unpack_from('<I', d, at)[0]
    else:parent = None
    return matrix, parent, d[20:20+n-1].decode('ascii')


class Skeleton:
    def __init__(self, resources):
        data = resources.get(0x130035F0)
        if len(data) != 248:raise ValueError('Unsupported Prince bone list')
        self.keys = list(struct.unpack('<62I', data))
        self.nodes = [node(resources, k) for k in self.keys]
        self.index = {k: i for i, k in enumerate(self.keys)}
        if len(self.index) != 62:raise ValueError('Duplicate bone')
        self.parents = [self.index[p] if p in self.index else -1 for _, p, _ in self.nodes]
        if any(p is not None and p not in self.index for _, p, _ in self.nodes):
            raise ValueError('External body bone parent')
        self.tracks = decode_tracks(resources.get(0x2D000AD4))
        if any(t['target'] not in (*range(62), 65535) for t in self.tracks):
            raise ValueError('Invalid bone track target')
        pairs = [(t['target'], t['kind']) for t in self.tracks]
        if len(set(pairs)) != len(pairs):raise ValueError('Duplicate transform channel')
        self.world(0)

    def world(self, tick):
        local = [m.copy() for m, _, _ in self.nodes]
        for t in self.tracks:
            if t['target'] == 65535:continue  # Actor motion is separate from the local skeleton.
            value = sample(t, tick)
            if t['kind'] == 'rotation':local[t['target']][:3, :3] = quaternion_matrix(value)
            else:local[t['target']][3, :3] = value
        result = {}; visiting = set()
        def visit(i):
            if i in visiting:raise ValueError('Cyclic skeleton')
            if i not in result:
                visiting.add(i)
                p = self.parents[i]
                result[i] = local[i] @ visit(p) if p >= 0 else local[i]
                visiting.remove(i)
            return result[i]
        return np.array([visit(i) for i in range(len(local))])

    def skin(self, component, tick):
        mesh = component['geometry'];world = self.world(tick)
        if mesh['weights'] is None:raise ValueError('Component has no skin')
        palette = np.array([b['inverse_bind'] @ world[self.index[int(link['key'], 16)]]
                           for b, link in zip(mesh['bones'], component['bindings'])])
        points = np.c_[mesh['position'], np.ones(len(mesh['position']))]
        return np.einsum('vb,bjk,vj->vk', mesh['weights'], palette, points)[:, :3]
