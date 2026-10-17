"""Model invariants and renderer comparison against the existing PS specimen."""
import json
import sys
import unittest
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_scene import MenuState,Scene


class ModelTests(unittest.TestCase):
    def setUp(self):
        entries=[dict(name='A',kind='choice',group='g',value='on'),dict(name='B',kind='choice',group='g',value='off'),dict(name='Key',kind='binding')]
        self.state=MenuState(dict(pages={p:dict(entries=entries) for p in ('keyboard','gamepad')}))
    def test_no_defaults(self):
        self.assertEqual(self.state.values,{})
        self.assertEqual(self.state.bindings,{})
    def test_exclusive_and_separate(self):
        self.state.choose('keyboard','g','on');self.state.choose('keyboard','g','off')
        self.state.choose('gamepad','g','on')
        self.assertEqual(self.state.values,{('keyboard','g'):'off',('gamepad','g'):'on'})
    def test_binding_validation(self):
        for value in ('','x'*25,'\n','é'):
            with self.assertRaises(ValueError):self.state.bind('keyboard','Key',value)
        with self.assertRaises(ValueError):self.state.bind('keyboard','missing','X')
    def test_unknown_choice(self):
        with self.assertRaises(ValueError):self.state.choose('keyboard','g','unknown')
        self.assertEqual(self.state.values,{})
    def test_clear_page_only(self):
        for page in ('keyboard','gamepad'):
            self.state.bind(page,'Key','X');self.state.choose(page,'g','on')
        self.state.clear('keyboard')
        self.assertEqual(self.state.bindings,{('gamepad','Key'):'X'})
        self.assertEqual(self.state.values,{('gamepad','g'):'on'})


def verify(folder,report):
    scene=Scene(folder);state=MenuState(scene.catalog)
    assert set(scene.catalog['pages'])=={'options','effects','advanced','keyboard','gamepad'}
    for page in scene.catalog['pages']:
        image,hits=scene.render(page,state)
        assert image.size==(800,600) and len(hits)>0
        for entry,rect in hits:
            assert 0<=rect[0]<rect[2]<=800 and 0<=rect[1]<rect[3]<=600,(page,entry['name'],rect)
    advanced=scene.catalog['pages']['advanced']['entries']
    assert [e['value'] for e in advanced if e.get('kind')=='choice']==['Trilinear','Bilinear','None','Disable','Enable','High','Low']
    for page,count in [('keyboard',12),('gamepad',6)]:
        assert sum(e.get('kind')=='binding' for e in scene.catalog['pages'][page]['entries'])==count
    # Independent PowerShell output is the alpha oracle for the reused layout formula.
    exp=json.loads((report/'experiment.json').read_text(encoding='utf-8-sig'))
    font=scene.fonts['Atlantis MF Regular 36']
    for row in exp['Rows']:
        image,*_=font.render(row['Text'],28.8,(255,255,255,255))
        with Image.open(report/row['Name']/'text.png') as original:
            alpha=original.getchannel('A');expected=alpha.crop(alpha.getbbox())
        assert image.size==expected.size
        assert ImageChops.difference(image.getchannel('A'),expected).getbbox() is None,row['Name']
    print('Five scenes verified; 18 binding fields; seven Advanced choices; six alpha renders match PowerShell exactly.')


if __name__=='__main__':
    if len(sys.argv)==3:
        folder,report=map(Path,sys.argv[1:]);sys.argv=sys.argv[:1];verify(folder,report)
    unittest.main()
