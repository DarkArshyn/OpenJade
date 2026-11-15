"""Capture fixed balcony poses and separately measure live frame timing.

Requires private prepared scene packages and the Vulkan screenshot layer.
Screenshots establish repeatability, not original-game pixel parity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from integration_prince_vulkan import verify

def run(scene, output, viewer):
    output.mkdir(parents=True, exist_ok=False)
    results = {}
    for seconds in (0., 1., 2., 3.983333, 4.):
        results[str(seconds)] = verify(scene, output / f'pose-{seconds:g}', viewer, seconds)
    env = dict(os.environ, OPENJADE_PROFILE_FRAMES='600', OPENJADE_PROFILE_PRESENT='fifo')
    for key in ('OPENJADE_CAPTURE_SECONDS', 'VK_INSTANCE_LAYERS', 'VK_SCREENSHOT_FRAMES', 'VK_SCREENSHOT_DIR'):
        env.pop(key, None)
    result = subprocess.run([str(viewer.resolve()), '--scene', str(scene.resolve()), '--color-pipeline',
                             'legacy-unorm', '--validation'], env=env, capture_output=True, text=True, timeout=90)
    text = result.stdout + result.stderr
    (output / 'frame-timing.txt').write_text(text, encoding='utf-8')
    if result.returncode or 'validation errors: 0' not in text or 'VUID-' in text:
        raise AssertionError('Live Vulkan timing run failed')
    results['scene_sha256'] = hashlib.sha256(scene.read_bytes()).hexdigest()
    results['scope'] = 'Fixed endpoint camera, repeatable poses and live timing; no native pixel parity or ground-contact proof.'
    (output / 'validation.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--viewer', type=Path, default=Path(__file__).resolve().parents[1] / 'engine/target/debug/jade-viewer.exe')
    args = parser.parse_args()
    run(args.scene, args.output, args.viewer)
