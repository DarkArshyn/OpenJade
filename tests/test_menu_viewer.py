"""Independent navigation model tests; widget construction has a separate smoke test."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_viewer import Selection

class SelectionTests(unittest.TestCase):
    def test_wrap(self):
        model=Selection(6)
        self.assertEqual(model.move(-1),5)
        self.assertEqual(model.move(1),0)
    def test_explicit_selection(self):
        model=Selection(6)
        model.choose(3)
        self.assertEqual(model.move(1),4)
    def test_invalid(self):
        with self.assertRaises(ValueError): Selection(0)
        model=Selection(6)
        for index in (-1,6):
            with self.assertRaises(ValueError): model.choose(index)
        self.assertEqual(model.index,0)

if __name__=='__main__': unittest.main()
