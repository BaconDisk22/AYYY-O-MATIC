#!/usr/bin/env python3
"""AYYY-O-MATIC desktop controller. Launch from the project checkout."""
import os
import sys
import subprocess
import runpy
import glob
from pathlib import Path
from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QHBoxLayout, QSystemTrayIcon, QMenu,
    QMessageBox, QStyle, QComboBox)

ROOT = Path(os.environ.get("AYYY_BOT_HOME", Path(__file__).resolve().parent.parent))
if getattr(sys, "frozen", False):
    ROOT = Path.home() / "Library" / "Application Support" / "AYYY-O-MATIC"
    ROOT.mkdir(parents=True, exist_ok=True)
    from shutil import copy2
    bundle = Path(getattr(sys, "_MEIPASS", ""))
    for name in ("mesh_bot.py", "config.template"):
        if not (ROOT / name).exists() and (bundle / name).exists():
            copy2(bundle / name, ROOT / name)
    if not (ROOT / "modules").exists() and (bundle / "modules").exists():
        from shutil import copytree
        copytree(bundle / "modules", ROOT / "modules")
    if not (ROOT / "etc").exists() and (bundle / "etc").exists():
        from shutil import copytree
        copytree(bundle / "etc", ROOT / "etc")
    if not (ROOT / "script").exists() and (bundle / "script").exists():
        from shutil import copytree
        copytree(bundle / "script", ROOT / "script")
GREEN, GOLD, DARK = "#1B5E20", "#F4B400", "#20252B"

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤌 AYYY-O-MATIC — The Garden State Mesh")
        self.resize(850, 580)
        self.setStyleSheet(f"""QWidget {{background:{DARK};color:#FFF5DF;font-size:14px}}
            QPushButton {{background:{GREEN};border:1px solid {GOLD};padding:11px;border-radius:8px}}
            QPushButton:hover {{background:#2E7D32}}
            QPlainTextEdit {{background:#121619;border:1px solid {GREEN};font-family:monospace}}
        """)
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.finished.connect(self.stopped)
        box = QWidget(); self.setCentralWidget(box)
        layout = QVBoxLayout(box)
        title = QLabel("🤌 AYYY-O-MATIC  📻"); title.setStyleSheet(f"font-size:30px;font-weight:bold;color:{GOLD}")
        layout.addWidget(title)
        layout.addWidget(QLabel("What exit? What node? You good?"))
        self.radio_ports = QComboBox()
        self.radio_ports.setEditable(True)
        layout.addWidget(QLabel("USB radio port"))
        layout.addWidget(self.radio_ports)
        refresh = QPushButton("Find USB radios")
        refresh.clicked.connect(self.detect_radios)
        layout.addWidget(refresh)
        self.detect_radios()
        self.status = QLabel("⚪ OFFLINE — Diner's closed, pal."); layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("▶ AYYY! START THE BOT")
        self.stop_button = QPushButton("■ CLOSE UP SHOP")
        self.start_button.clicked.connect(self.start_bot)
        self.stop_button.clicked.connect(self.stop_bot)
        self.stop_button.setEnabled(False)
        buttons.addWidget(self.start_button); buttons.addWidget(self.stop_button)
        layout.addLayout(buttons)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); layout.addWidget(self.log)
        self.log.appendPlainText(f"Bot directory: {ROOT}")
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
            menu = QMenu()
            show = QAction("Open the diner", self); show.triggered.connect(self.showNormal); menu.addAction(show)
            start = QAction("Start bot", self); start.triggered.connect(self.start_bot); menu.addAction(start)
            stop = QAction("Stop bot", self); stop.triggered.connect(self.stop_bot); menu.addAction(stop)
            quit_action = QAction("Quit AYYY-O-MATIC", self); quit_action.triggered.connect(self.quit_app); menu.addAction(quit_action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)
            self.tray.show()
        self.quitting = False

    def detect_radios(self):
        previous = self.radio_ports.currentText()
        devices = sorted(set(glob.glob("/dev/cu.usb*") + glob.glob("/dev/tty.usb*")))
        self.radio_ports.clear()
        self.radio_ports.addItems(devices)
        if previous and previous not in devices:
            self.radio_ports.addItem(previous)
        if previous:
            self.radio_ports.setCurrentText(previous)

    def start_bot(self):
        if self.process.state() != QProcess.NotRunning: return
        script = ROOT / "mesh_bot.py"
        python = Path(sys.executable) if getattr(sys, "frozen", False) else ROOT / "venv" / "bin" / "python3"
        if not script.is_file() or not python.is_file():
            QMessageBox.warning(self, "Ayyy! Setup needed",
                "Bot source or virtual environment missing. Install the original project's dependencies first.\n"
                f"Expected: {script}\n{python}")
            return
        config = ROOT / "config.ini"
        template = ROOT / "config.template"
        if not config.exists() and template.exists():
            config.write_bytes(template.read_bytes())
        selected = self.radio_ports.currentText().strip()
        if selected and (ROOT / "config.ini").exists():
            import configparser
            parser = configparser.ConfigParser()
            parser.read(ROOT / "config.ini")
            if parser.has_section("interface"):
                parser.set("interface", "type", "serial")
                parser.set("interface", "port", selected)
                with (ROOT / "config.ini").open("w") as output:
                    parser.write(output)
        from PySide6.QtCore import QProcessEnvironment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)
        self.process.start(str(python), ["--bot"] if getattr(sys, "frozen", False) else [str(script)])
        if not self.process.waitForStarted(3000):
            self.log.appendPlainText("Failed to start bot: " + self.process.errorString())
            return
        self.status.setText("🟢 RUNNING — We're open for business!")
        self.start_button.setEnabled(False); self.stop_button.setEnabled(True)

    def read_log(self):
        self.log.appendPlainText(bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace").rstrip())

    def stop_bot(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(2500):
                self.process.kill(); self.process.waitForFinished(1000)

    def stopped(self, *args):
        self.status.setText("⚪ OFFLINE — Stuck on the Turnpike.")
        self.start_button.setEnabled(True); self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        if self.tray and not self.quitting:
            self.hide(); event.ignore()
            self.tray.showMessage("AYYY-O-MATIC", "Still runnin' in the menu bar, boss!")
        else:
            self.stop_bot(); event.accept()

    def quit_app(self):
        self.quitting = True; self.close()
        QApplication.instance().quit()

if __name__ == "__main__":
    if "--bot" in sys.argv:
        os.chdir(ROOT)
        sys.argv = [str(ROOT / "mesh_bot.py")]
        runpy.run_path(str(ROOT / "mesh_bot.py"), run_name="__main__")
        sys.exit(0)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = Dashboard(); window.show()
    sys.exit(app.exec())
