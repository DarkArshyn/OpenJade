"""Sky/moon state and export tests using synthetic resources only."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_sky_state import decode_sky
from menu_fog_state import transform_fog_points
from export_engine_materials import convert


def material(key):
    moon=key=='0x30000D1B'
    return struct.pack('<12I',5,6,0,0,0,0,0,0x14607 if moon else 0x6007,
                       0,0x3f800000,0x80000000 if moon else 0,123)


class SkyTests(unittest.TestCase):
    def test_distinct_material_states(self):
        moon=decode_sky(material('0x30000D1B'),'0x30000D1B')
        sky=decode_sky(material('0x30000CAC'),'0x30000CAC')
        self.assertEqual((moon['blend'],moon['depth_write'],moon['rgb_gain']),(1,False,1))
        self.assertAlmostEqual(moon['alpha'],128/255)
        self.assertEqual((sky['blend'],sky['depth_write'],sky['rgb_gain']),(0,True,2))
        self.assertEqual(moon['scale'],[1,1])

    def test_unknown_rotation_rejected(self):
        data=bytearray(material('0x30000D1B'));data[40]=1
        with self.assertRaises(ValueError):decode_sky(data,'0x30000D1B')

    def test_scale_before_rotation_and_translation(self):
        matrix=np.array([[0,1,0,2],[-1,0,0,3],[0,0,1,.5],[10,20,30,1.]])
        np.testing.assert_allclose(transform_fog_points(np.array([[1,2,4]]),matrix),[[4,22,32]])

    def test_export_blend_alpha_and_single_constant_gain(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);source=p/'source';source.mkdir();objects=[];materials=[];lines=[]
            for i,(key,mode,name) in enumerate([('0x30000D1B',2,'2100_ciel_nuit_lune.gao'),('0x30000CAC',3,'Menu3D_sky.gao'),('0x30000CAC',3,'Menu3D_ground.gao')]):
                objects.append(dict(name=name,triangles=1,omitted_groups=[],fog_states=[],color_groups=[dict(material=key,mode=mode,constant_rgb=[86,102,118])]))
                materials.append(dict(slot=i,key=key,stages=None,sky_state=decode_sky(material(key),key)))
                b=i*3+1
                lines.extend([f'o {name}','v 0 0 2 .1 .2 .3','v 1 0 2 .1 .2 .3','v 0 1 2 .1 .2 .3','vt 0 0','vt 1 0','vt 0 1',f'usemtl material-{i}',f'f {b}/{b} {b+1}/{b+1} {b+2}/{b+2}'])
                Image.new('RGBA',(2,2),(40,60,80,128)).save(source/f'material-{i}.png')
            (source/'scene.obj').write_text('\n'.join(lines))
            (source/'scene.json').write_text(json.dumps(dict(source_sha256='synthetic',accepted=objects,materials=materials,fog_time=0)))
            camera=p/'poses.json';camera.write_text(json.dumps(dict(source_sha256='synthetic',vertical_fov=60,poses=[dict(time=0,matrix=np.eye(4).tolist())])))
            convert(source,camera,p/'out')
            result=json.loads((p/'out/manifest.json').read_text());draws=result['draws']
            self.assertEqual([d['object'] for d in draws],['Menu3D_sky.gao','Menu3D_ground.gao','2100_ciel_nuit_lune.gao'])
            self.assertEqual([d['depth_write'] for d in draws],[True,True,False])
            self.assertEqual([d['parameters'][5] for d in draws],[2,1,1])
            self.assertEqual([d['parameters'][6] for d in draws],[0,.5,0])
            self.assertAlmostEqual(draws[2]['parameters'][4],128/255)
            blob=(p/'out/menu.ojscene').read_bytes()
            self.assertAlmostEqual(struct.unpack_from('<f',blob,76+6*36+20)[0],172/255)


if __name__=='__main__':unittest.main()
