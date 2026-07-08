# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Added
- Integrated `google-genai` SDK targeting both Google AI Studio (`GEMINI_API_KEY`) and Google Cloud Vertex AI (`gemini-3.5-flash` on `global`).
- Integrated `divoom-protocol` (`DivoomClient`) for asynchronous Bluetooth Low Energy transmission to Divoom Timebox Evo with smart BLE name matching fallback (`Timebox-Evo-light`) and a resilient 5-attempt connection retry loop with exponential backoff.
- Added automated Linux Bluetooth controller wake-up (`ensure_bluetooth_ready` running `rfkill unblock bluetooth` and `hciconfig hci0 up`) prior to scanning/connecting.
- Added structured JSON grid schema validation and tuple flattening helpers.
- Added comprehensive high-surprise video game and pop culture `THEMES` catalog in `src/script.py`.
- Added asynchronous HTTP Webhook API (`src/server.py` on port `8080`) providing `/refresh`, `/status`, and `/health` endpoints alongside periodic background scheduling.
- Added full unit test suites in `tests/test_script.py`, `tests/test_scan_bluetooth.py`, and `tests/test_server.py`.
- Added Dockerfile and CasaOS/Raspberry Pi compatible `docker-compose.yml` with `/run/dbus`, `/var/run/dbus`, and `/sys/class/bluetooth` volume mounts for full Linux BlueZ compatibility.
