"""Regression coverage for measured PC material-pack selection."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from prince_resources import material_slot

class MaterialSlots(unittest.TestCase):
    def test_sword_groups_resolve_to_source_pack_entries(self):
        pack=[0x13006BBB,0x13006BBC]
        self.assertEqual([pack[material_slot(pack,x)] for x in [0,2,4]],
                         [0x13006BBB,0x13006BBC,0x13006BBC])

    def test_bounds_are_independent_of_sword_identifiers(self):
        pack=[17,29,41]
        self.assertEqual([material_slot(pack,x) for x in [0,1,2,3,999]],[0,1,2,2,2])
        self.assertEqual(material_slot([73],4),0)

    def test_unverified_empty_and_negative_inputs_are_rejected(self):
        for pack,index in [([],0),([17],-1),([17],1.5)]:
            with self.assertRaises(ValueError):material_slot(pack,index)

if __name__=="__main__":unittest.main()
