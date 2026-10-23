import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from inspect_menu_scene_links import static_links


class SceneLinkTests(unittest.TestCase):
    def fixture(self, extended=False):
        name=b'test.gao\0'
        offset=len(name)+122+(24 if extended else 0)
        d=bytearray(offset+8)
        d[:4]=b'.gao'
        struct.pack_into('<4I',d,4,10,8,0x4000|(0x80000 if extended else 0),len(name))
        d[20:20+len(name)]=name
        struct.pack_into('<2I',d,offset,123,456)
        return d

    def test_both_volume_layouts(self):
        for extended in (False, True):
            result=static_links(self.fixture(extended))
            self.assertEqual(result['mesh'],'0x0000007B')
            self.assertEqual(result['material_pack'],'0x000001C8')
            self.assertEqual(result['link_offset'],131+24*extended)

    def test_truncation_and_nonstatic(self):
        d=self.fixture(); bad=bytearray(d); struct.pack_into('<I',bad,12,0)
        for invalid in (d[:19],d[:-1],bad):
            with self.assertRaises(ValueError): static_links(invalid)


if __name__=='__main__': unittest.main()
