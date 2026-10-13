"""State precedence and real MGM palette checks for the research viewer."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_viewer import state_for,load_state_colors

class StateTests(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(state_for(1,0,None,None),'ENABLED')
        self.assertEqual(state_for(0,0,None,None),'SELECTED')
    def test_precedence(self):
        self.assertEqual(state_for(0,0,0,None),'OVER')
        self.assertEqual(state_for(0,0,0,0),'PRESSED')
        self.assertEqual(state_for(0,0,0,0,True),'DISABLED')
    def test_drag_away(self):
        self.assertEqual(state_for(0,1,1,0),'ENABLED')

if __name__=='__main__':
    if len(sys.argv)>1:
        colors=load_state_colors(Path(sys.argv.pop()))
        assert len(colors)==6
        for palette in colors:
            assert palette==dict(ENABLED=(188,160,122,255),SELECTED=(188,160,122,255),OVER=(232,220,193,255),PRESSED=(255,255,255,255),DISABLED=(102,102,102,255))
        print('Six real MGM palettes verified.')
    unittest.main()
