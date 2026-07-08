# PixelGrid: Divoom Timebox Evo & Vertex AI Gemini Service

Automated container webservice and Python tool that uses Google Cloud Vertex AI Gemini (`gemini-3.5-flash` on `global`) to generate retro 16x16 pixel art arrays and push them to a Divoom Timebox Evo display over Bluetooth Low Energy (BLE).

## Architecture & Webhook Server (`port 8080`)

The service runs an asynchronous `aiohttp` web server on port `8080` while managing a periodic background generation loop (`LOOP_INTERVAL_MINUTES=15`).

### HTTP Endpoints
- `GET /refresh` or `POST /refresh`: Instantly generates a new 16x16 artwork theme, saves it to `/app/downloads/`, and transmits it to your Divoom speaker over BLE.
- `GET /status`: Returns JSON detailing the last generated artwork theme, timestamp, filepath, and BLE transmission status.
- `GET /health`: Returns service health status (`200 OK`).

## Quick Setup (Local Development)

1. Create virtual environment and install dependencies:
   ```bash
   make setup
   source .venv/bin/activate
   ```
2. Run unit tests:
   ```bash
   make test
   ```
3. Generate a single JSON grid (no Bluetooth required):
   ```bash
   make run-once
   ```
4. Start the Webhook & Scheduled Server locally:
   ```bash
   uv run python src/server.py --port 8080 --interval 15
   ```

## Running on Raspberry Pi / CasaOS via Docker Compose

To enable BLE access from inside a container on a Raspberry Pi Linux host:
1. Set your `DIVOOM_MAC_ADDRESS` in `docker-compose.yml`.
2. Start the background service:
   ```bash
   docker-compose up -d --build
   ```
3. Trigger an instant artwork refresh anytime from your browser or CasaOS dashboard:
   ```bash
   curl http://<raspberry-pi-ip>:8080/refresh
   ```
