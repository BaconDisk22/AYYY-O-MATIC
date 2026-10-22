"""Exercise the real dashboard with a harmless temporary bot, never radio hardware."""
import configparser
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess
from desktop import ayyy_o_matic as ui


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(ui, 'ROOT', self.root)
        self.root_patch.start()
        self.tray_patch = patch.object(ui.QSystemTrayIcon, 'isSystemTrayAvailable', return_value=False)
        self.tray_patch.start()
        self.window = ui.Dashboard()

    def tearDown(self):
        self.window.quitting = True
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()
        self.tray_patch.stop()
        self.root_patch.stop()
        self.temp.cleanup()

    def test_start_output_and_stop_preserve_radio_config(self):
        executable = self.root / 'venv/bin/python3'
        executable.parent.mkdir(parents=True)
        executable.symlink_to(sys.executable)
        (self.root / 'mesh_bot.py').write_text('import time\nprint("test activity", flush=True)\ntime.sleep(30)\n')
        (self.root / 'config.template').write_text('[interface]\ntype=tcp\nport=old\n[general]\nname=preserved\n')
        self.window.radio_ports.setCurrentText('/dev/test-radio')
        self.window.start_button.click()
        self.assertEqual(self.window.status.text(), 'RUNNING')
        self.assertFalse(self.window.start_button.isEnabled())
        deadline = time.monotonic() + 5
        while self.window.event_count == 0 and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.01)
        self.assertIn('test activity', self.window.log.toPlainText())
        parser = configparser.ConfigParser()
        parser.read(self.root / 'config.ini')
        self.assertEqual(parser['interface']['port'], '/dev/test-radio')
        self.assertEqual(parser['general']['name'], 'preserved')
        self.window.started_at = time.monotonic() - 65
        self.window.update_uptime()
        self.assertEqual(self.window.uptime_label.text(), '00:01:05')
        self.window.stop_button.click()
        self.assertEqual(self.window.process.state(), QProcess.NotRunning)
        self.assertEqual(self.window.status.text(), 'OFFLINE')
        self.assertTrue(self.window.start_button.isEnabled())
        self.assertEqual(self.window.uptime_label.text(), '00:00:00')

    def test_manual_port_survives_refresh_and_export_is_utf8(self):
        self.window.radio_ports.setCurrentText('/dev/manual')
        with patch.object(ui.glob, 'glob', return_value=[]):
            self.window.detect_radios()
        self.assertEqual(self.window.radio_ports.currentText(), '/dev/manual')
        self.window.log.setPlainText('Pumpkin 🎃')
        destination = self.root / 'export.txt'
        with patch.object(ui.QFileDialog, 'getSaveFileName', return_value=(str(destination), '')):
            self.window.export_log()
        self.assertEqual(destination.read_text(), 'Pumpkin 🎃\n')

    def test_config_created_from_template_and_opened(self):
        (self.root / 'config.template').write_text('[interface]\ntype=serial\n')
        with patch.object(ui.QDesktopServices, 'openUrl') as open_url:
            self.window.config_button.click()
        self.assertEqual((self.root / 'config.ini').read_text(), '[interface]\ntype=serial\n')
        self.assertEqual(open_url.call_args.args[0].toLocalFile(), str(self.root / 'config.ini'))


if __name__ == '__main__':
    unittest.main()
