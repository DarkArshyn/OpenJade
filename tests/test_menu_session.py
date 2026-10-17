"""Regression checks for session transactions, including shared slider domains."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_simulation import SettingsSession


class Transactions(unittest.TestCase):
    def setUp(self):
        self.model=SimpleNamespace(values={},bindings={},sliders={})
        self.session=SettingsSession(self.model)

    def test_commit_then_discard_all_settings(self):
        self.model.values[('effects','Item1')]='Medium'
        self.model.bindings[('keyboard','Key_1_1')]='Z'
        self.model.sliders[('graphics','Gamma')]=43
        self.session.commit()
        self.model.values.clear(); self.model.bindings.clear(); self.model.sliders.clear()
        self.assertTrue(self.session.dirty)
        self.session.discard()
        self.assertEqual(self.model.sliders[('graphics','Gamma')],43)
        self.assertEqual(self.model.bindings[('keyboard','Key_1_1')],'Z')
        self.assertEqual(self.model.values[('effects','Item1')],'Medium')
        self.assertFalse(self.session.dirty)

    def test_discard_does_not_alias_saved_state(self):
        self.session.discard()
        self.model.values['new']='value'
        self.assertTrue(self.session.dirty)
        self.session.discard()
        self.assertEqual(self.model.values,{})

    def test_restoring_original_value_is_not_dirty(self):
        self.model.sliders['shared']=3
        self.session.commit()
        self.model.sliders['shared']=4
        self.model.sliders['shared']=3
        self.assertFalse(self.session.dirty)


if __name__=='__main__': unittest.main()
