import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from preview_menu3d_landmarks import mesh_groups, clip_polygon, raster


def fixture():
    h = 108
    data = bytearray(h + 8 + 60 + 4 + 12)
    struct.pack_into('<I', data, 16, 3)
    struct.pack_into('<I', data, 32, 2)
    points = [(0., 0., 0.), (1., 0., 0.), (0., 1., 0.)]
    for i, point in enumerate(points):
        struct.pack_into('<3f', data, 44 + 12*i, *point)
        struct.pack_into('<5f', data, h + 8 + 20*i, *point, 0., 0.)
    struct.pack_into('<7I', data, 80, 2, 7, 1, 12, 1, 68, 0)
    struct.pack_into('<2I', data, h, 3, 20)
    struct.pack_into('<I6H', data, h + 68, 12, 0, 1, 2, 2, 1, 0)
    return data, h


class LandmarkTests(unittest.TestCase):
    def test_groups(self):
        data, h = fixture()
        vertices, triangles, groups = mesh_groups(bytes(data), h)
        self.assertEqual(groups, [(7, 1), (12, 1)])
        self.assertEqual(triangles.tolist(), [[0, 1, 2], [2, 1, 0]])
        self.assertEqual(vertices.shape, (3, 5))

    def test_reject_corrupt_counts_indices_and_positions(self):
        for offset, fmt, value in [(88, '<I', 2), (180, '<H', 3), (116, '<f', 9.)]:
            data, h = fixture()
            struct.pack_into(fmt, data, offset, value)
            with self.assertRaises(ValueError):
                mesh_groups(bytes(data), h)

    def test_reject_truncation(self):
        data, h = fixture()
        with self.assertRaises(ValueError):
            mesh_groups(bytes(data[:-1]), h)

    def test_clip_preserves_interpolated_uv(self):
        polygon = [np.array(p, dtype=float) for p in
                   [(0, 0, -1, 0, 0), (2, 0, 1, 1, 0), (0, 2, 1, 0, 1)]]
        clipped = clip_polygon(polygon)
        self.assertEqual(len(clipped), 4)
        self.assertTrue(all(p[2] >= .1 - 1e-12 for p in clipped))
        crossings = [p for p in clipped if abs(p[2] - .1) < 1e-12]
        self.assertEqual(len(crossings), 2)
        self.assertAlmostEqual(sum(crossings[0][3:]), .55)

    def test_depth_and_transparency(self):
        def obj(distance, slot):
            return dict(vertices=np.array([[-1, -distance, -1], [1, -distance, -1], [0, -distance, 1]]),
                        uv=np.zeros((3, 2)), triangles=np.array([[0, 1, 2]]), groups=[(slot, 1)])
        textures = {0: np.array([[[255, 0, 0, 255]]]), 1: np.array([[[0, 255, 0, 255]]])}
        for objects in [[obj(2, 0), obj(3, 1)], [obj(3, 1), obj(2, 0)]]:
            result, _, _ = raster(objects, textures, np.zeros(3), np.eye(3), 60)
            self.assertEqual(result.getpixel((400, 300)), (255, 0, 0))
        textures[0][0, 0, 3] = 0
        result, _, _ = raster([obj(2, 0), obj(3, 1)], textures, np.zeros(3), np.eye(3), 60)
        self.assertEqual(result.getpixel((400, 300)), (0, 255, 0))


if __name__ == '__main__':
    unittest.main()

