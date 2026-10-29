"""Synthetic bridge and transaction tests; no original game data required."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from graphics_settings import SettingsBridge,parse
from simulation_screens import Model

class GraphicsSettingsTests(unittest.TestCase):
    def test_validation(self):
        for text in ['OJSET001\n101\n0','OJSET001\n-1\n0','OJSET001\n+1\n0','OJSET001\n1\n2\n3','OJSET002\n0\n0']:
            with self.assertRaises(ValueError):parse(text)
    def test_preview_save_discard_defaults_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'settings.ojsettings';bridge=SettingsBridge(path);model=Model()
            def publish():
                bridge.publish(round(float(model.settings['graphics'][1])*100),round(float(model.saved['graphics'][1])*100))
                return parse(path.read_text())
            self.assertEqual(publish(),(0,0))
            model.settings['graphics'][1]='0.42';self.assertEqual(publish(),(42,0))
            model.save();self.assertEqual(publish(),(42,42))
            model.settings['graphics'][1]='1.00';self.assertEqual(publish(),(100,42))
            model.discard();self.assertEqual(publish(),(42,42))
            model.defaults('advanced');self.assertEqual(publish(),(0,42))
            self.assertEqual(SettingsBridge(path).saved,42)
            model.save();self.assertEqual(publish(),(0,0));self.assertEqual(SettingsBridge(path).saved,0)
    def test_unrelated_file_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'settings.ojsettings';path.write_text('unrelated')
            with self.assertRaises(ValueError):SettingsBridge(path)
            self.assertEqual(path.read_text(),'unrelated')

if __name__=='__main__':unittest.main()
