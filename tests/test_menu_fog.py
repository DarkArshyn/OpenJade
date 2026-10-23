"""Synthetic regressions for raw pixels, untextured geometry and fog compositing."""
import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from assemble_menu_scene import texture_image
from menu_primary_geometry import primary_mesh
from menu_colored_raster import raster


class MenuFogTests(unittest.TestCase):
    def test_raw_bgra_and_extent(self):
        data = bytearray(60)
        struct.pack_into('<HH', data, 12, 1, 1)
        struct.pack_into('<3I', data, 40, 0, 1, 1)
        data[56:] = bytes([10, 20, 30, 128])
        self.assertEqual(texture_image(bytes(data)).getpixel((0, 0)), (30, 20, 10, 128))
        for invalid in (data[:-1], data + b'\0'):
            with self.assertRaises(ValueError):
                texture_image(bytes(invalid))

    def test_mesh_without_uv(self):
        data = struct.pack('<11I', 1, 7, 0, 0, 3, 0, 0, 0, 1, 0, 0)
        data += struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
        data += struct.pack('<Ii8H', 1, 0, 0, 1, 2, 65535, 65535, 65535, 0, 0)
        vertices, *_ = primary_mesh(data)
        np.testing.assert_array_equal(vertices[:, 3:], np.zeros((3, 2)))
        with self.assertRaises(ValueError):
            primary_mesh(data[:-1])

    def test_blending_depth_and_order(self):
        def obj(distance, slot, blend):
            return dict(vertices=np.array([[-1, -distance, -1], [1, -distance, -1], [0, -distance, 1]]),
                        uv=np.zeros((3, 2)), colors=np.ones((3, 3)),
                        triangles=np.array([[0, 1, 2]]), groups=[(slot, 1)], blend=blend)
        textures = {0: np.array([[[100, 0, 0, 255]]], dtype=np.uint8),
                    1: np.array([[[0, 100, 0, 128]]], dtype=np.uint8),
                    2: np.array([[[0, 0, 100, 128]]], dtype=np.uint8)}
        def pixel(objects):
            image, *_ = raster(objects, textures, np.zeros(3), np.eye(3), 60)
            return image.getpixel((400, 300))
        self.assertEqual(pixel([obj(3, 0, False), obj(2, 1, True)]), (49, 50, 0))
        self.assertEqual(pixel([obj(3, 0, False), obj(4, 1, True)]), (100, 0, 0))
        layers = [obj(3, 0, False), obj(2, 1, True), obj(1, 2, True)]
        self.assertEqual(pixel(layers), pixel(layers[::-1]))
        self.assertEqual(pixel(layers), (24, 24, 50))


if __name__ == '__main__':
    unittest.main()
