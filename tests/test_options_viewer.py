import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from options_viewer import EffectsModel,load_options

class EffectsTests(unittest.TestCase):
    def setUp(self):
        self.model=EffectsModel([dict(name='a',choices=[dict(name='x'),dict(name='y')])])
    def test_unset(self):
        self.assertIsNone(self.model.values['a'])
    def test_exclusive(self):
        self.model.choose('a','x');self.model.choose('a','y')
        self.assertEqual(self.model.values,{'a':'y'})
    def test_clear(self):
        self.model.choose('a','x');self.model.clear()
        self.assertIsNone(self.model.values['a'])
    def test_invalid(self):
        with self.assertRaises(ValueError): self.model.choose('a','z')
        with self.assertRaises(ValueError): self.model.choose('missing','x')

if __name__=='__main__':
    if len(sys.argv)>1:
        data=load_options(Path(sys.argv.pop()))
        assert [len(g['choices']) for g in data['groups']]==[3,3,2,2]
        assert [c['text'] for c in data['groups'][1]['choices']]==['High','Low','None']
        print('Real MGM: four groups and ten non-empty choices verified.')
    unittest.main()
