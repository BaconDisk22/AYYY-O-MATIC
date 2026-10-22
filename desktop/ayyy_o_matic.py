#!/usr/bin/env python3
"""AYYY-O-MATIC desktop controller. Launch from the project checkout."""
import os
import sys
import runpy
import glob
import shutil
import time
from pathlib import Path
from PySide6.QtCore import QProcess, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QFrame, QLabel, QPushButton, QPlainTextEdit, QHBoxLayout, QSystemTrayIcon, QMenu,
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
# Shared Halloween tokens; no external fonts or assets required by the app bundle.
ORANGE, PURPLE, GREEN = "#FF8A3D", "#B79AFF", "#BDFA63"
DARK, PANEL, TEXT, MUTED = "#0D0B12", "#18131F", "#F6F0FA", "#B5A9C2"

class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AYYY-O-MATIC — After Dark")
        self.resize(1040, 780)
        self.setMinimumSize(680, 660)
        self.setStyleSheet(f"""
            QWidget {{background:{DARK};color:{TEXT};font-family:"Avenir Next","Segoe UI",sans-serif;font-size:14px;}}
            QFrame#panel {{background:{PANEL};border:1px solid #36283F;border-radius:14px;}}
            QFrame#panel QLabel {{background:transparent;border:0;}}
            QLabel#eyebrow {{color:{PURPLE};font-size:11px;font-weight:700;letter-spacing:2px;}}
            QLabel#title {{color:{ORANGE};font-size:34px;font-weight:800;letter-spacing:-1px;}}
            QLabel#subtitle, QLabel#muted {{color:{MUTED};font-size:12px;}}
            QLabel#edition {{color:{ORANGE};background:#2C1B17;border:1px solid #684027;border-radius:8px;padding:8px;font-size:11px;font-weight:700;}}
            QLabel#metric {{color:{GREEN};font-family:"Menlo","Consolas",monospace;font-size:23px;font-weight:600;}}
            QLabel#status {{color:{MUTED};font-size:17px;font-weight:700;}}
            QLabel#status[state="running"] {{color:{GREEN};}}
            QLabel#status[state="demo"] {{color:{PURPLE};}}
            QLabel#status[state="error"] {{color:{ORANGE};}}
            QPushButton {{background:#241B30;border:1px solid #51405F;padding:10px 16px;border-radius:8px;font-weight:600;}}
            QPushButton:hover {{background:#382748;border-color:{PURPLE};}}
            QPushButton:pressed {{background:#49325D;}}
            QPushButton:focus, QComboBox:focus, QPlainTextEdit:focus {{border:2px solid {PURPLE};}}
            QPushButton#primary {{background:{ORANGE};color:{DARK};border-color:{ORANGE};}}
            QPushButton#primary:hover {{background:#FFAD70;}}
            QPushButton#primary:pressed {{background:#E87529;}}
            QPushButton:disabled, QPushButton#primary:disabled {{background:#211C28;color:#81768C;border:1px solid #393140;}}
            QComboBox {{background:#100D16;border:1px solid #51405F;padding:10px;border-radius:8px;}}
            QComboBox QAbstractItemView {{background:{PANEL};color:{TEXT};selection-background-color:#49325D;}}
            QPlainTextEdit {{background:#0B0910;color:#D8CFE2;border:1px solid #36283F;border-radius:10px;padding:12px;font-family:"Menlo","Consolas",monospace;font-size:12px;selection-background-color:#49325D;}}
            QMenu {{background:{PANEL};border:1px solid #51405F;padding:6px;}}
            QMenu::item {{padding:8px 18px;}}
            QMenu::item:selected {{background:#49325D;}}
            QToolTip {{background:{PANEL};color:{TEXT};border:1px solid {PURPLE};}}
        """)
        self.started_at = None
        self.event_count = 0
        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_log)
        self.process.finished.connect(self.stopped)
        self.uptime_timer = QTimer(self)
        self.uptime_timer.timeout.connect(self.update_uptime)
        self.uptime_timer.start(1000)
        box = QWidget(); self.setCentralWidget(box)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        header = QHBoxLayout()
        identity = QVBoxLayout()
        eyebrow = QLabel("GARDEN STATE MESH / AFTER DARK"); eyebrow.setObjectName("eyebrow")
        title = QLabel("AYYY-O-MATIC"); title.setObjectName("title")
        subtitle = QLabel("Keep the mesh alive. Even after midnight."); subtitle.setObjectName("subtitle")
        identity.addWidget(eyebrow); identity.addWidget(title); identity.addWidget(subtitle)
        header.addLayout(identity, 1)
        edition = QLabel("HALLOWEEN\nEDITION / 01"); edition.setObjectName("edition")
        edition.setAlignment(Qt.AlignCenter)
        header.addWidget(edition)
        layout.addLayout(header)

        metrics = QHBoxLayout(); metrics.setSpacing(12)
        self.status = QLabel(); self.status.setObjectName("status")
        self.uptime_label = QLabel("00:00:00"); self.uptime_label.setObjectName("metric")
        self.events_label = QLabel("0"); self.events_label.setObjectName("metric")
        for caption, value, hint in (
            ("BOT STATUS", self.status, "Controller process"),
            ("SESSION UPTIME", self.uptime_label, "Since the last start"),
            ("LOG EVENTS", self.events_label, "Output lines received"),
        ):
            card = QFrame(); card.setObjectName("panel")
            card_layout = QVBoxLayout(card); card_layout.setContentsMargins(18, 14, 18, 14)
            label = QLabel(caption); label.setObjectName("eyebrow")
            footnote = QLabel(hint); footnote.setObjectName("muted")
            card_layout.addWidget(label); card_layout.addWidget(value); card_layout.addWidget(footnote)
            metrics.addWidget(card, 1)
        self.set_status("offline", "OFFLINE")
        layout.addLayout(metrics)

        radio_panel = QFrame(); radio_panel.setObjectName("panel")
        radio_layout = QVBoxLayout(radio_panel); radio_layout.setContentsMargins(18, 16, 18, 16)
        radio_heading = QLabel("01 / RADIO CONNECTION"); radio_heading.setObjectName("eyebrow")
        radio_layout.addWidget(radio_heading)
        self.radio_ports = QComboBox(); self.radio_ports.setEditable(True)
        self.radio_ports.setAccessibleName("USB radio port")
        self.radio_ports.setMinimumWidth(160)
        radio_row = QHBoxLayout()
        radio_label = QLabel("USB port"); radio_label.setBuddy(self.radio_ports)
        radio_row.addWidget(radio_label); radio_row.addWidget(self.radio_ports, 1)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setToolTip("Scan for connected USB radios")
        self.refresh_button.clicked.connect(self.detect_radios)
        radio_row.addWidget(self.refresh_button)
        radio_layout.addLayout(radio_row)
        self.detect_radios()
        controls = QHBoxLayout()
        self.start_button = QPushButton("Start bot"); self.start_button.setObjectName("primary")
        self.stop_button = QPushButton("Stop bot")
        self.config_button = QPushButton("Open config")
        self.start_button.clicked.connect(self.start_bot)
        self.stop_button.clicked.connect(self.stop_bot)
        self.config_button.clicked.connect(self.open_config)
        self.stop_button.setEnabled(False)
        controls.addWidget(self.start_button, 1); controls.addWidget(self.stop_button, 1)
        controls.addWidget(self.config_button)
        radio_layout.addLayout(controls)
        layout.addWidget(radio_panel)

        log_header = QHBoxLayout()
        log_title = QLabel("02 / ACTIVITY LOG"); log_title.setObjectName("eyebrow")
        log_header.addWidget(log_title); log_header.addStretch()
        export = QPushButton("Export log"); export.clicked.connect(self.export_log)
        log_header.addWidget(export)
        layout.addLayout(log_header)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.log.setAccessibleName("Bot activity log")
        self.log.document().setMaximumBlockCount(3000)
        layout.addWidget(self.log, 1)
        self.log.appendPlainText(f"Bot directory: {ROOT}")
        self.footer = QLabel("JERSEY DEVIL HOURS  /  Real mesh. No tricks.")
        self.footer.setObjectName("muted"); layout.addWidget(self.footer)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(self.style().standardIcon(QStyle.SP_ComputerIcon), self)
            menu = QMenu()
            show = QAction("Open dashboard", self); show.triggered.connect(self.showNormal); menu.addAction(show)
            start = QAction("Start bot", self); start.triggered.connect(self.start_bot); menu.addAction(start)
            stop = QAction("Stop bot", self); stop.triggered.connect(self.stop_bot); menu.addAction(stop)
            quit_action = QAction("Quit AYYY-O-MATIC", self); quit_action.triggered.connect(self.quit_app); menu.addAction(quit_action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.Trigger else None)
            self.tray.show()
        self.quitting = False

    def set_status(self, state, text):
        """Use both text and color so state never depends on color alone."""
        self.status.setText(text)
        self.status.setProperty("state", state)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

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
                Path(filename).write_text(self.log.toPlainText() + "\n", encoding="utf-8")
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
            self.set_status("error", "START FAILED")
            self.log.appendPlainText("Failed to start bot: " + self.process.errorString())
            return
        self.set_status("running", "RUNNING")
        self.started_at = time.monotonic()
        self.start_button.setEnabled(False); self.stop_button.setEnabled(True)

    def read_log(self):
        chunk = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if chunk.strip():
            self.log.appendPlainText(chunk.rstrip())
            self.event_count += len(chunk.splitlines())
            self.events_label.setText(f"{self.event_count:,}")
            self.log.document().setMaximumBlockCount(3000)

    def stop_bot(self):
        if self.process.state() != QProcess.NotRunning:
            self.process.terminate()
            if not self.process.waitForFinished(2500):
                self.process.kill(); self.process.waitForFinished(1000)

    def update_uptime(self):
        if self.started_at is not None and self.process.state() != QProcess.NotRunning:
            elapsed = int(time.monotonic() - self.started_at)
            hours, rem = divmod(elapsed, 3600)
            minutes, seconds = divmod(rem, 60)
            self.uptime_label.setText(f"{hours:02}:{minutes:02}:{seconds:02}")

    def stopped(self, *args):
        self.started_at = None
        self.uptime_label.setText("00:00:00")
        self.set_status("offline", "OFFLINE")
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
        window.set_status("demo", "DEMO MODE")
        window.uptime_label.setText("00:18:42")
        window.events_label.setText("6")
        window.radio_ports.clear()
        window.radio_ports.addItem("/dev/cu.usbserial-DEMO (sample)")
        window.log.clear()
        for line in (
            "[DEMO] Garden State Mesh / After Dark — sample session",
            "[DEMO] 10:15 Node NJ-CRYPT joined the mesh",
            "[DEMO] 10:16 Message from NJ-PUMPKIN: AYYY! Signal's good.",
            "[DEMO] 10:17 Node NJ-DEVIL battery: 87%",
            "[DEMO] 10:18 Radio link: simulated, no hardware required",
            "[DEMO] This screenshot contains synthetic demonstration data.",
        ):
            window.log.appendPlainText(line)
        window.footer.setText("DEMO / Synthetic data. No radio connected. No bot process running.")
        window.radio_ports.setEnabled(False)
        window.refresh_button.setEnabled(False)
        window.config_button.setEnabled(False)
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
