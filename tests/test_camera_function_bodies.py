import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from resolve_camera_function_bodies import function_body

def node(tag): return dict(tag=tag,category=tag>>24)
class BodyTests(unittest.TestCase):
    def test_stops_at_next_definition(self):
        nodes=[node(0x1c005b82),node(0x05000025),node(0x1d000000),node(0x1c005b83)]
        self.assertEqual(len(function_body(nodes,0x5b82)),3)
    def test_ambiguity_and_missing_end(self):
        for tags in [[],[0x1c005b82,0x1c005b82],[0x1c005b82,0x05000025,0x1c005b83]]:
            with self.assertRaises(ValueError):function_body([node(t) for t in tags],0x5b82)
if __name__=='__main__':unittest.main()
