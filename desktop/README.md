# 🎃 AYYY-O-MATIC / After Dark

Native Python / Qt desktop controller with a Halloween palette, readable activity console, USB port selector, process status, uptime, and log counters. Bot commands and emergency messages remain unchanged.

## Intel Mac setup

Download an unsigned development preview from [Releases](https://github.com/BaconDisk22/AYYY-O-MATIC/releases). The Intel build workflow creates an x86_64 `.app`, ZIP, DMG and SHA256 checksums. Consult the workflow run for the exact revision that was packaged. Hardware connectivity still requires a configured Meshtastic radio.

For source use, follow [INSTALL.md](../INSTALL.md) to install bot dependencies into `venv`, then:

```sh
venv/bin/python -m pip install PySide6
venv/bin/python desktop/ayyy_o_matic.py
```

The controller starts `venv/bin/python3 mesh_bot.py` from the repository root. Select or type the USB port, use **Open config** to edit configuration, and choose **Start bot**. **RUNNING** means the process started; it does not assert that a radio is connected. **Export log** saves the displayed console as UTF-8 text. The console retains up to 3,000 blocks.

Closing the window hides it in the menu bar when a tray is available. **Quit AYYY-O-MATIC** stops the process and exits. Set `AYYY_BOT_HOME` to an absolute checkout path for source runs. Packaged apps keep configuration and bot data under `~/Library/Application Support/AYYY-O-MATIC` as before.

## Preview and checks

```sh
venv/bin/python desktop/ayyy_o_matic.py --demo
QT_QPA_PLATFORM=offscreen venv/bin/python desktop/ayyy_o_matic.py --demo-screenshot screenshots/ayyy-o-matic-dashboard.png
QT_QPA_PLATFORM=offscreen venv/bin/python -m unittest discover -s desktop/tests -v
```

Demo mode shows synthetic data and disables radio, config and process controls. It never starts the bot. Screenshots use the same widgets as the live app, with no additional assets or downloaded fonts required.

## Wireless connections

Choose **USB / Serial**, **Wi-Fi / TCP**, or **Bluetooth LE** in the dashboard. For TCP, enter a reachable Meshtastic host such as `meshtastic.local:4403` (or its IP address). For BLE, enter the device identifier accepted by the installed Meshtastic Python library; macOS may require Bluetooth permission. Connection availability depends on the radio firmware and hardware. The selection updates the existing `[interface]` configuration without overwriting other settings. A RUNNING process is not proof of a successful radio connection; check the activity log.
