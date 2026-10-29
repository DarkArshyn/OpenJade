"""Synthetic regression tests for material export; no original assets required."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from export_engine_materials import pass_parameters, convert, balcony_gain, BALCONY

class MaterialExportTests(unittest.TestCase):
    def test_balcony_experiment_is_bounded(self):
        self.assertEqual(balcony_gain(BALCONY,0,None,True),2.)
        for name,mode,stages,enabled in [(BALCONY,2,None,True),(BALCONY,3,None,True),('tree',0,None,True),(BALCONY,0,[{}],True),(BALCONY,0,None,False)]:
            self.assertEqual(balcony_gain(name,mode,stages,enabled),1.)

    def test_static_and_dynamic_offsets(self):
        stage=dict(flags=0x40000000,blend=6,depth_write=False,scale=[2.,3.],rate=[.1,.2],alpha=.5)
        mode,p=pass_parameters(stage,3.)
        self.assertEqual(mode,6);self.assertAlmostEqual(p[2],.3);self.assertAlmostEqual(p[3],.2)
        self.assertEqual(p[4:],[.5,2.,0.,1.])
    def test_rejects_unknown_depth_state(self):
        with self.assertRaises(ValueError): pass_parameters(dict(flags=0,blend=6,depth_write=True),0)
    def test_exports_fog_last_and_keeps_fixture_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'in';source.mkdir()
            fog=dict(flags='0x40014205',motion=dict(rate_u=.125))
            stage=dict(flags=0xC0066207,blend=6,depth_write=False,scale=[1.,1.],rate=[0.,0.],alpha=1.)
            objects=[];materials=[];lines=[]
            for i,(name,states,stages,mode) in enumerate([('fog',[fog],None,2),('wall',[],None,2),('fire',[],[stage,stage],3)]):
                key=f'm{i}'
                objects.append(dict(name=name,triangles=1,omitted_groups=[],fog_states=states,color_groups=[dict(material=key,mode=mode,constant_rgb=[64,128,192])]))
                materials.append(dict(slot=i,key=key,stages=stages))
                base=i*3+1
                lines += [f'o {name}','v 0 0 2 .1 .2 .3','v 1 0 2 .1 .2 .3','v 0 1 2 .1 .2 .3','vt 0 1','vt 1 1','vt 0 0',f'usemtl material-{i}',f'f {base}/{base} {base+1}/{base+1} {base+2}/{base+2}']
                for suffix in (['-stage-0','-stage-1'] if stages else ['']):
                    image=Image.new('RGBA',(2,1)); image.putdata([(50,100,150,128),(1,2,3,4)]); image.save(source/f'material-{i}{suffix}.png')
            (source/'scene.obj').write_text('\n'.join(lines))
            (source/'scene.json').write_text(json.dumps(dict(source_sha256='fixture',accepted=objects,materials=materials,fog_time=1.)))
            camera=root/'poses.json';camera.write_text(json.dumps(dict(source_sha256='fixture',vertical_fov=60,poses=[dict(time=0,matrix=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]])])))
            convert(source,camera,root/'out',3.)
            with self.assertRaisesRegex(ValueError,'Unsupported balcony'):
                convert(source,camera,root/'invalid',3.,True)
            self.assertFalse((root/'invalid').exists())
            manifest=json.loads((root/'out/manifest.json').read_text())
            self.assertEqual([d['object'] for d in manifest['draws']],['wall','fire','fire','fog'])
            self.assertEqual([d['blend'] for d in manifest['draws']],[0,6,6,1])
            self.assertEqual([d['depth_write'] for d in manifest['draws']],[True,False,False,False])
            self.assertAlmostEqual(manifest['draws'][-1]['parameters'][2],.25)
            blob=(root/'out/menu.ojscene').read_bytes()
            self.assertEqual(blob[:8],b'OJSCN003')
            pixel_start=76+struct.unpack_from('<I',blob,8)[0]*36
            self.assertEqual(blob[pixel_start:pixel_start+12],bytes([50,100,150,128,1,2,3,4,0,0,0,0]))
            self.assertEqual(struct.unpack_from('<8I',blob,len(blob)-32),(2,1)*4)
            self.assertAlmostEqual(struct.unpack_from('<f',blob,76+20)[0],128/255)
            self.assertEqual(manifest['geometry_triangles'],3);self.assertEqual(manifest['submitted_triangles'],4)

if __name__=='__main__':unittest.main()
