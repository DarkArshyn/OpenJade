"""Behavior and rendering checks for the screenshot-driven simulation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from simulation_screens import Model,BASELINE,ACTIONS,Screens


class ModelTests(unittest.TestCase):
    def test_profiles_validate_and_select(self):
        m=Model();m.create(' Prince ')
        self.assertEqual(m.active,'Prince')
        for name in ['', 'prince', '../'+('x'*21), '\x00']:
            with self.assertRaises(ValueError):m.create(name)
        self.assertEqual(m.profiles,['Prince'])

    def test_scroll_reaches_all_actions(self):
        m=Model();seen=set()
        for _ in range(5):seen.update(ACTIONS[m.offset:m.offset+6]);m.scroll(5)
        self.assertEqual(seen,set(ACTIONS));self.assertEqual(m.offset,len(ACTIONS)-6)
        m.scroll(-100);self.assertEqual(m.offset,0)

    def test_transaction_restores_bindings_and_shared_controls(self):
        m=Model();m.settings['keyboard'][-1][1]='K';m.settings['controls'][0]='90';m.save()
        m.defaults('gamepad');self.assertTrue(m.dirty);m.discard()
        self.assertEqual(m.settings['keyboard'][-1][1],'K')
        self.assertEqual(m.settings['controls'][0],'90')
        self.assertEqual(BASELINE['controls'][0],'43')

    def test_reset_is_local_to_settings_family(self):
        m=Model();m.settings['sound'][0]='0';m.settings['graphics'][0]='640x480x32'
        m.defaults('effects');self.assertEqual(m.settings['sound'][0],'0')
        self.assertEqual(m.settings['graphics'][0],'800x600x32')


if __name__=='__main__':
    report=Path(sys.argv.pop()) if len(sys.argv)>1 else None
    result=unittest.main(exit=False)
    if not result.result.wasSuccessful():raise SystemExit(1)
    if report:
        s=Screens(report);m=Model();m.create('Prince')
        for page in ['main','options','effects','advanced','keyboard','gamepad','game','sound','profiles','create']:
            image,hits=s.render(page,m)
            assert image.size==(800,600) and hits,page
            for action,(x,y,r,b) in hits:assert 0<=x<r<=800 and 0<=y<b<=600,(page,action,(x,y,r,b))
        for modal in ['settings','quit','delete']:
            _,hits=s.render('game',m,modal=modal)
            assert all(action[0]=='answer' for action,_ in hits)
        print('Ten screens and three exclusive confirmation layouts validated.')
