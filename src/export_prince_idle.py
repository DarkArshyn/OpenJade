"""Export the original alternative Prince clip as an optional bounded actor sidecar."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from prince_resources import Resources
from prince_animation import Skeleton, decode_tracks


def export(actor, output, sources):
    if output.exists():
        raise ValueError("Output already exists")
    data = actor.read_bytes()
    if data[:8] != b"OJACT001":
        raise ValueError("Unsupported actor")
    nb, nt, nv, rate, duration = struct.unpack_from("<3I2f", data, 8)
    resources = Resources(sources)
    skeleton = Skeleton(resources)
    if (nb, rate, duration) != (62, 5., 20.):
        raise ValueError("Unsupported base clip")
    bones = b"".join(struct.pack("<i16f", parent, *matrix.ravel())
                     for parent, (matrix, _, _) in zip(skeleton.parents, skeleton.nodes))
    if data[28:28 + len(bones)] != bones:
        raise ValueError("Actor skeleton differs from source")
    at = 28 + len(bones)
    for _ in range(nt):
        _, _, count = struct.unpack_from("<3I", data, at)
        at += 12 + 20 * count
        if at > len(data):
            raise ValueError("Truncated actor tracks")
    clip = resources.get(0x330010E9)
    tracks = [t for t in decode_tracks(clip) if t["target"] != 65535]
    if max(t["duration_ticks"] for t in tracks) != 73:
        raise ValueError("Unexpected source clip duration")
    result = bytearray(b"OJACT001") + struct.pack("<3I2f", nb, len(tracks), nv, 5., 73.) + bones
    for track in tracks:
        rotation = track["kind"] == "rotation"
        result += struct.pack("<3I", track["target"], 0 if rotation else 1, len(track["keys"]))
        for key in track["keys"]:
            value = np.asarray(key["values"], float) / (32768 if rotation else 1)
            if not rotation:
                value = np.r_[value, 0.]
            result += struct.pack("<5f", key["tick"], *value)
    result += data[at:]
    output.write_bytes(result)
    return {"clip": "330010E9", "source_sha256": hashlib.sha256(clip).hexdigest(),
            "tracks": len(tracks), "duration_ticks": 73, "sidecar": str(output),
            "sha256": hashlib.sha256(result).hexdigest()}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("actor", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--sources", nargs="+", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(export(args.actor, args.output, args.sources), indent=2))
