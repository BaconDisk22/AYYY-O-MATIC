# AYYY-O-MATIC / Halloween theme

The Garden State identity continues after dark. The desktop theme is implemented in `desktop/ayyy_o_matic.py` with shared color tokens and native Qt widgets; no external font or image assets are needed at runtime.

| Role | Color | Usage |
|---|---|---|
| Pumpkin orange | `#FF8A3D` | Title, primary action, start failure |
| Midnight black | `#0D0B12` | Window background |
| Eerie purple | `#B79AFF` | Section labels, focus rings, demo status |
| Acid green | `#BDFA63` | Running status, session metrics |
| Panel | `#18131F` | Cards and connection controls |
| Main text | `#F6F0FA` | Labels and controls |
| Muted text | `#B5A9C2` | Supporting information and offline status |

Typography uses Avenir Next / Segoe UI with a sans-serif fallback. Menlo / Consolas keeps counters and logs easy to scan. Rounded panels group status, connection and activity. Keyboard focus uses a purple outline. Status always includes text, not just color.

Use seasonal personality in headings and demonstration data. Keep operational controls, emergency alerts, raw logs, command syntax and security messages clear. RUNNING describes the bot process, not verified radio connectivity. Demo data must be labeled and must not start a real bot.

Based on [Meshing Around](https://github.com/SpudGunMan/meshing-around); upstream licensing, attribution, commands and configuration are preserved.
