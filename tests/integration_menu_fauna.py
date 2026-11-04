"""Compare bird atlas timing and fly texture transforms to local GOG draw captures."""
import argparse
import json
from pathlib import Path
import struct


def check_atlas(directory):
    times = dict((int(frame),float(dt)) for frame,dt in
                 (row.split() for row in (directory/"birds-track-clock.txt").read_text().splitlines()))
    intervals = 0
    for family,delay in [(0,10),(1,2)]:
        poses = []
        for path in sorted(directory.glob(f"birds-track-*-{family:03d}.particles")):
            flags, = struct.unpack_from("<I",path.read_bytes())
            poses.append((int(path.stem.split("-")[2]),flags))
        for (start,flags),(end,next_flags) in zip(poses,poses[1:]):
            tile = (flags >> 8) & 127
            reverse = bool(flags & 32768)
            counter = (flags >> 16) & 255
            for frame in range(start+1,end+1):
                if counter < delay:
                    counter = int(counter + times[frame]*120)
                else:
                    counter = 0
                    tile += -1 if reverse else 1
                    if tile < 0:
                        tile,reverse = 1,False
                    elif tile > 7:
                        tile,reverse = 6,True
            assert (counter<<16 | int(reverse)<<15 | tile<<8) == next_flags & 0xffff00
            intervals += 1
    if not intervals:
        raise ValueError("Missing consecutive bird observations")
    return intervals


def check_flies(directory):
    times = {}
    for row in (directory/"fauna-material-log.txt").read_text().splitlines():
        frame,dt,*_ = row.split()
        times[int(frame)] = float(dt)
    checked = 0
    for path in sorted(directory.glob("*.constants")):
        if not path.with_suffix(".txt").read_text().startswith("54 0 1 "):
            continue
        frame = int(path.stem.split("-")[2])
        seconds = sum(times[i] for i in range(frame+1))
        u,_,du,_,_,v,dv,_ = struct.unpack_from("<8f",path.read_bytes(),12*16)
        assert (u,v)==(1.390625,1.)
        assert abs((du-seconds*1.390625+0.5)%1-0.5)<0.00001
        assert abs((dv-seconds*(-0.0098876953125)+0.5)%1-0.5)<0.00001
        checked += 1
    if not checked:
        raise ValueError("Missing fly draws")
    return checked


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_root",type=Path)
    directory=parser.parse_args().capture_root
    print(json.dumps(dict(bird_intervals=check_atlas(directory/"birds-track"),
                          fly_transforms=check_flies(directory/"fauna-material"))))
