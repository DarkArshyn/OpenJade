"""Fit yaw, pitch and FOV to manually identified image correspondences.

The position and scene remain fixed. Pixel coordinates are estimated observations,
not native camera data. This ray fit assumes a pinhole camera without lens distortion.
"""
import argparse
import json
import math
from pathlib import Path
import numpy as np


def basis(parameters):
    yaw, pitch, _ = np.radians(parameters)
    right = np.array([math.cos(yaw), math.sin(yaw), 0.])
    forward = np.array([math.sin(yaw), -math.cos(yaw), 0.])
    up = np.array([0., 0., 1.])
    up, forward = math.cos(pitch)*up-math.sin(pitch)*forward, math.sin(pitch)*up+math.cos(pitch)*forward
    return np.array([right, -forward, up])


def project_pixels(pixels, previous, candidate):
    pixels = np.asarray(pixels, dtype=float)
    focal = 300/math.tan(math.radians(previous[2])/2)
    rays = np.column_stack(((pixels[:, 0]-400)/focal, -np.ones(len(pixels)), (300-pixels[:, 1])/focal)) @ basis(previous)
    view = rays @ basis(candidate).T
    focal = 300/math.tan(math.radians(candidate[2])/2)
    if np.any(view[:, 1] >= 0):
        raise ValueError('Landmark behind candidate camera')
    return np.column_stack((400-focal*view[:, 0]/view[:, 1], 300+focal*view[:, 2]/view[:, 1]))


def fit(source, target, sigma, previous):
    source, target = np.asarray(source), np.asarray(target)
    sigma = np.asarray(sigma)[:, None]
    if len(source) < 3 or not np.all(sigma > 0):
        raise ValueError('At least three landmarks and positive uncertainties required')
    parameters = np.array(previous, dtype=float)
    for _ in range(80):
        residual = ((project_pixels(source, previous, parameters)-target)/sigma).ravel()
        jacobian = np.column_stack([(((project_pixels(source, previous, parameters+np.eye(3)[k]*1e-4)-target)/sigma).ravel()-residual)/1e-4 for k in range(3)])
        if np.linalg.matrix_rank(jacobian) < 3:
            raise ValueError('Degenerate landmark configuration')
        step = np.linalg.lstsq(jacobian, -residual, rcond=None)[0]
        improved = False
        for scale in (1., .5, .25, .125, .0625):
            trial = parameters + step*scale
            if not (20 < trial[2] < 100 and abs(trial[0]) < 45 and abs(trial[1]) < 30):
                continue
            error = ((project_pixels(source, previous, trial)-target)/sigma).ravel()
            if error @ error < residual @ residual:
                parameters = trial
                improved = True
                break
        if not improved or np.linalg.norm(step) < 1e-7:
            break
    return parameters


def run(input_path, output):
    data = json.loads(input_path.read_text(encoding='utf-8'))
    points = data['landmarks']; previous = data['previous_camera']
    source = np.array([p['preview_pixel'] for p in points]); target = np.array([p['reference_pixel'] for p in points])
    sigma = np.array([p['uncertainty_pixels'] for p in points])
    active = np.array([p.get('use_for_fit',True) for p in points])
    parameters = fit(source[active], target[active], sigma[active], previous)
    predicted = project_pixels(source, previous, parameters)
    for i, point in enumerate(points):
        keep = active & (np.arange(len(points)) != i)
        alternative = fit(source[keep], target[keep], sigma[keep], previous) if sum(keep)>=3 else None
        point.update(predicted_pixel=predicted[i].tolist(), residual_pixels=float(np.linalg.norm(predicted[i]-target[i])),
                     leave_one_out_error=float(np.linalg.norm(project_pixels(source[i:i+1], previous, alternative)[0]-target[i])) if alternative is not None else None,
                     leave_one_out_camera=alternative.tolist() if alternative is not None else None)
    data.update(fitted_camera=parameters.tolist(), before_rms_pixels=float(np.sqrt(np.mean(np.sum((source-target)**2, axis=1)))),
                after_rms_pixels=float(np.sqrt(np.mean(np.sum((predicted-target)**2, axis=1)))),
                fit_landmark_count=int(sum(active)),
                fit_rms_pixels=float(np.sqrt(np.mean(np.sum((predicted[active]-target[active])**2, axis=1)))),
                status='Manual correspondence fit; not a recovered native camera')
    output.write_text(json.dumps(data, indent=2), encoding='utf-8')
    print(json.dumps({k:data[k] for k in ('fitted_camera','before_rms_pixels','after_rms_pixels')}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('landmarks', type=Path); parser.add_argument('output', type=Path)
    args=parser.parse_args(); run(args.landmarks, args.output)
