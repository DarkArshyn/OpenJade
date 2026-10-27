"""Synthetic checks for the OBJ-to-engine bridge; no game assets required."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from export_engine_scene import convert

class SceneBridgeTests(unittest.TestCase):
    def fixture(self, root):
        source = root / 'source'; source.mkdir()
        report = dict(source_sha256='fixture', materials=[dict(key='test',slot=0,stages=None)],
                      accepted=[dict(name='test.gao',fog_states=[],omitted_groups=[],color_groups=[dict(material='test')],triangles=1)])
        (source/'scene.json').write_text(json.dumps(report))
        (source/'scene.obj').write_text('o test.gao\nv 1 2 3 .1 .2 .3\nv 4 5 6 .4 .5 .6\nv 7 8 9 .7 .8 .9\nvt .25 .75\nvt 0 1\nvt 1 0\nusemtl material-0\nf 1/1 2/2 3/3\n')
        Image.new('RGBA',(1,1),(20,40,60,255)).save(source/'material-0.png')
        camera=root/'poses.json'
        camera.write_text(json.dumps(dict(source_sha256='fixture',vertical_fov=60,poses=[dict(time=0,matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[10,20,30,1]])])))
        return source,camera
    def test_preserves_world_vertices_colors_and_reverses_obj_v(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source,camera=self.fixture(root)
            convert(source,camera,root/'out')
            data=(root/'out/menu.ojscene').read_bytes()
            camera_values=struct.unpack_from('<13f',data,24)
            self.assertEqual(camera_values,(10,20,30,-1,0,0,0,0,1,0,-1,0,60))
            vertex=struct.unpack_from('<9f',data,76)
            self.assertEqual(vertex[:5],(1,2,3,.25,.25))
            self.assertAlmostEqual(vertex[5],.1)
            self.assertEqual(data[-4:],bytes([20,40,60,255]))
    def test_rejects_different_source_and_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source,camera=self.fixture(root)
            convert(source,camera,root/'out')
            original=(root/'out/menu.ojscene').read_bytes()
            with self.assertRaises(FileExistsError): convert(source,camera,root/'out')
            self.assertEqual(original,(root/'out/menu.ojscene').read_bytes())
            doc=json.loads(camera.read_text());doc['source_sha256']='different';camera.write_text(json.dumps(doc))
            with self.assertRaises(ValueError): convert(source,camera,root/'other')
            self.assertFalse((root/'other').exists())

if __name__=='__main__': unittest.main()
