# 🤌 AYYY-O-MATIC Mac dashboard (development preview)

This is the first **working-source implementation** of the New Jersey-themed desktop controller. It starts/stops the existing Meshtastic Python bot, shows live output, and minimizes to the macOS menu bar when available.

## Intel Mac setup

From the repository root, follow the upstream `INSTALL.md` to install bot dependencies into `venv`, configure `config.ini` from `config.template`, and verify the bot starts. Then install PySide6 into an available Python environment:

```bash
python3 -m pip install PySide6
python3 desktop/ayyy_o_matic.py
```

The desktop controller launches `venv/bin/python3 mesh_bot.py` from the repository root. Closing the window hides it in the menu bar when a system tray is available; choose **Quit AYYY-O-MATIC** from the menu bar to stop the bot and exit. Set `AYYY_BOT_HOME` to an absolute checkout path if launching from another location.

**Important:** This is source code, **not yet a double-clickable standalone `.app` or `.dmg`**. No Intel Tahoe build has been produced or tested yet. PyInstaller packaging will need an explicit persistent writable bot directory and dependency handling; simply freezing this controller will not bundle the bot's runtime and configuration. Avoid hardcoded Linux CA bundle paths from the upstream shell launcher on macOS. Emergency alerts remain unchanged.
