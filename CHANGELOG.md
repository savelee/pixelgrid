# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Added pure helper `upscale_matrix` to upscale 8x8 pixel art 2x into 16x16 LED matrices.
- Added pure helper `center_pixel_matrix` to automatically center foreground sprites inside square LED matrices.
- Support for `--grid-size` CLI argument (defaults to `8`).

### Changed
- Default pixel art generation resolution changed from 16x16 to 8x8 for sharper 8-bit retro gaming aesthetics.
- Default periodic generation interval changed from 15 minutes to 10 minutes (`LOOP_INTERVAL_MINUTES=10`).
- Updated `THEMES` list to specific 8-bit arcade and console subjects (including Princess Peach, Mario, Link, Samus, Pac-Man, etc.).

- Integrated `google-genai` SDK targeting both Google AI Studio (`GEMINI_API_KEY`) and Google Cloud Vertex AI (`gemini-3.5-flash` on `global`).
- Integrated `divoom-protocol` (`DivoomClient`) for asynchronous Bluetooth Low Energy transmission to Divoom Timebox Evo with smart BLE name matching fallback (`Timebox-Evo-light`) and a resilient 5-attempt connection retry loop with exponential backoff.
- Added automated Linux Bluetooth controller wake-up (`ensure_bluetooth_ready` running `rfkill unblock bluetooth` and `hciconfig hci0 up`) prior to scanning/connecting.
- Added structured JSON grid schema validation and tuple flattening helpers.
- Added comprehensive high-surprise video game and pop culture `THEMES` catalog in `src/script.py`.
- Added asynchronous HTTP Webhook API (`src/server.py` on port `8080`) providing `/refresh`, `/status`, and `/health` endpoints alongside periodic background scheduling.
- Added full unit test suites in `tests/test_script.py`, `tests/test_scan_bluetooth.py`, and `tests/test_server.py`.
- Added Dockerfile and CasaOS/Raspberry Pi compatible `docker-compose.yml` with `/run/dbus`, `/var/run/dbus`, and `/sys/class/bluetooth` volume mounts for full Linux BlueZ compatibility.
