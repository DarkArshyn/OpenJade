import struct, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from assemble_menu_scene import decode_mesh, material_keys, texture_image


class AssemblyTests(unittest.TestCase):
    def fixture(self):
        d=bytearray(182)
        struct.pack_into('<2I',d,0,1,7)
        struct.pack_into('<I',d,16,3)
        struct.pack_into('<I',d,32,1)
        points=[(0,0,0),(1,0,0),(0,1,0)]
        for i,p in enumerate(points):
            struct.pack_into('<3f',d,44+i*12,*p)
            struct.pack_into('<5f',d,112+i*20,*p,0,0)
        struct.pack_into('<6I',d,84,1,0,1,68,0,3)
        struct.pack_into('<I',d,108,20)
        struct.pack_into('<I3H',d,172,6,0,1,2)
        return d

    def test_validated_mesh_and_invalid_indices(self):
        d=self.fixture()
        h,(vertices,triangles,groups)=decode_mesh(d)
        self.assertEqual(h,104)
        self.assertEqual(groups,[(0,1)])
        self.assertEqual(triangles.tolist(),[[0,1,2]])
        struct.pack_into('<H',d,180,3)
        with self.assertRaises(ValueError):decode_mesh(d)

    def test_xyz_must_match_primary_data(self):
        d=self.fixture();struct.pack_into('<f',d,112,99)
        with self.assertRaises(ValueError):decode_mesh(d)

    def test_pack_extent_and_short_texture(self):
        d=struct.pack('<5I',4,0,2,123,456)
        self.assertEqual(material_keys(d),[123,456])
        with self.assertRaises(ValueError):material_keys(d[:-1])
        with self.assertRaises(ValueError):texture_image(bytes(55))


if __name__=='__main__':unittest.main()
