"""Regression tests for the experimental coverage expansion and generated artifacts."""
import json
import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_style_experiment import thicken_right


class ExpansionTests(unittest.TestCase):
    def test_preserves_origin_and_last_column(self):
        source=Image.fromarray(np.array([[40,200]],dtype=np.uint8))
        self.assertEqual(np.asarray(thicken_right(source)).tolist(),[[40,200,200]])
        self.assertEqual(np.asarray(source).tolist(),[[40,200]])

    def test_does_not_wrap_rows(self):
        source=Image.fromarray(np.array([[0,255],[0,0]],dtype=np.uint8))
        self.assertEqual(np.asarray(thicken_right(source)).tolist(),[[0,255,255],[0,0,0]])

    def test_keeps_transparency(self):
        source=Image.new('L',(2,2))
        self.assertIsNone(thicken_right(source).getbbox())


def verify_report(root):
    report=json.loads((root/'style-results.json').read_text())
    assert len(report['variants'])==12
    assert len({v['name'] for v in report['variants']})==12
    assert report['prototype_style']=='bilinear-none'
    assert not report['game_rendering_validated']
    for variant in report['variants']:
        assert len(variant['rows'])==6
        assert all(0<=v<=1 for v in variant['mean_dice_by_threshold'])
    for name in ('prototype','style-candidate'):
        with Image.open(root/(name+'.png')) as preview, Image.open(root/(name+'-transparent.png')) as layer:
            assert preview.size==layer.size==(800,600)
            assert layer.getpixel((799,599))[3]==0
            assert preview.getpixel((799,599))==(24,28,36)
            assert layer.getchannel('A').getbbox() is not None
    print('Artifact checks passed: 12 variants, 6 labels each, two 800x600 previews and transparent layers.')


if __name__=='__main__':
    if len(sys.argv)>1:
        verify_report(Path(sys.argv.pop()))
    unittest.main()
