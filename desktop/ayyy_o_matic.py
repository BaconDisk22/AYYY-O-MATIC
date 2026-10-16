#!/usr/bin/env python3
"""AYYY-O-MATIC desktop controller. Launch from the project checkout."""
import os
import sys
import subprocess
import runpy
import glob
import shutil
from pathlib import Path
from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QPlainTextEdit, QHBoxLayout, QSystemTrayIcon, QMenu,
    QMessageBox, QStyle, QComboBox, QFileDialog)

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
        self.resize(920, 650)
        self.setMinimumSize(680, 470)
        self.setStyleSheet(f"""QWidget {{background:{DARK};color:#FFF5DF;font-size:14px}}
            QPushButton {{background:{GREEN};border:1px solid {GOLD};padding:11px;border-radius:8px}}
            QPushButton:hover {{background:#2E7D32}}
            QPushButton:disabled {{background:#424A48;color:#A9B4AE;border-color:#52605A}}
            QComboBox {{background:#151D1B;border:1px solid #637C68;padding:7px;border-radius:5px}}
            QLabel#subtitle {{color:#B9D2C0;font-size:12px}}
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
        subtitle = QLabel("GARDEN STATE MESH CONTROL  •  What exit? What node? You good?")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)
        self.radio_ports = QComboBox()
        self.radio_ports.setEditable(True)
        radio_row = QHBoxLayout()
        radio_row.addWidget(QLabel("USB RADIO"))
        radio_row.addWidget(self.radio_ports, 1)
        refresh = QPushButton("Refresh ports")
        refresh.clicked.connect(self.detect_radios)
        radio_row.addWidget(refresh)
        layout.addLayout(radio_row)
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
        if not devices and not previous:
            self.radio_ports.setPlaceholderText("No USB radio detected")
        if previous and previous not in devices:
            self.radio_ports.addItem(previous)
        if previous:
            self.radio_ports.setCurrentText(previous)

    def export_log(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export AYYY-O-MATIC log", str(Path.home() / "AYYY-O-MATIC-log.txt"),
            "Text files (*.txt)")
        if filename:
            try:
                Path(filename).write_text(self.log.toPlainText() + "\\n", encoding="utf-8")
            except OSError as exc:
                QMessageBox.warning(self, "Export failed", str(exc))

    def open_config(self):
        config = ROOT / "config.ini"
        if not config.exists():
            template = ROOT / "config.template"
            if template.is_file():
                shutil.copy2(template, config)
        if config.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(config)))
        else:
            QMessageBox.warning(self, "Configuration missing", f"No config found in {ROOT}")

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
    demo = "--demo" in sys.argv or "--demo-screenshot" in sys.argv
    app.setQuitOnLastWindowClosed(False)
    window = Dashboard()
    if demo:
        window.setWindowTitle("AYYY-O-MATIC — DEMO / SAMPLE DATA")
        window.status.setText("🟡 DEMO MODE — No radio connected")
        window.radio_ports.clear()
        window.radio_ports.addItem("/dev/cu.usbserial-DEMO (sample)")
        window.log.clear()
        for line in (
            "[DEMO] Welcome to the Garden State Mesh!",
            "[DEMO] 10:15 Node NJ-DINER joined the mesh",
            "[DEMO] 10:16 Message from NJ-SHORE: AYYY! Signal's good.",
            "[DEMO] 10:17 Node NJ-PARKWAY battery: 87%",
            "[DEMO] 10:18 Radio link: simulated, no hardware required",
            "[DEMO] This screenshot contains synthetic demonstration data.",
        ):
            window.log.appendPlainText(line)
        window.start_button.setEnabled(False)
        window.stop_button.setEnabled(False)
        window.tray.hide() if window.tray else None
    window.show()
    if "--demo-screenshot" in sys.argv:
        index = sys.argv.index("--demo-screenshot")
        if index + 1 >= len(sys.argv):
            raise SystemExit("--demo-screenshot requires an output PNG path")
        output = Path(sys.argv[index + 1]).expanduser().resolve()
        def capture():
            output.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(output), "PNG"):
                raise RuntimeError("Screenshot capture failed")
            app.quit()
        QTimer.singleShot(700, capture)
    sys.exit(app.exec())
