# PixelGrid: Autonomous AI Pixel Art Service for Divoom Timebox Evo

PixelGrid is an autonomous containerized service designed to run 24/7 on a **Raspberry Pi (CasaOS / Linux)**. Every 10 minutes, it uses Google AI Studio or Google Cloud Vertex AI Gemini models (`gemini-2.5-flash` / `gemini-3.5-flash`) to generate authentic **8x8 retro 8-bit video game sprites**, automatically centers and upscales them 2x into 16x16 pixel art arrays, and renders them directly onto a physical **Divoom Timebox Evo** LED speaker over Bluetooth Low Energy (BLE).

---

## ✨ Key Features

- **8-Bit Retro Sprite Engine:** Generates clean 8x8 RGB sprites (`grid_size=8`) from curated classic arcade, NES, and 8-bit console themes.
- **Automatic Matrix Centering & Upscaling:**
  - **Auto-Centering (`center_pixel_matrix`):** Automatically calculates the foreground sprite bounding box against the background color and centers the sprite on the canvas.
  - **2x Programmatic Upscaling (`upscale_matrix`):** Expands each 8x8 pixel into a 2x2 LED block on the 16x16 Divoom display for authentic retro chunky aesthetics.
- **Dual Authentication:** Supports completely free **Google AI Studio API Keys (`GEMINI_API_KEY`)** alongside enterprise Google Cloud Vertex AI Application Default Credentials (ADC).
- **Self-Healing Linux BLE Pipeline:**
  - **Automated Hardware Wakeup (`ensure_bluetooth_ready`):** Automatically executes `rfkill unblock bluetooth` and `hciconfig hci0 up` inside the privileged container before every transmission to prevent adapter sleep states.
  - **BlueZ Discovery Warmup:** Actively scans airwaves for 10 seconds (`BleakScanner.find_device_by_address`) to warm up Linux BlueZ's kernel cache before connecting.
  - **5-Attempt Exponential Backoff:** Resilient retry loop automatically recovers from transient RF drops or busy controller locks.
- **Webhook API (`port 8080`):** Includes a built-in asynchronous HTTP server offering instant on-demand generation (`/refresh`), real-time status diagnostics (`/status`), and health probes (`/health`).
- **Archive History:** Automatically stores every generated JSON array in `./downloads/` with timestamped filenames.

---

## 🎨 How the Prompt & Matrix Generation Works (`src/script.py`)

PixelGrid generates physical LED artwork without using heavy image generation models by prompting Gemini (`gemini-2.5-flash` / `gemini-3.5-flash`) to produce structured numerical JSON matrices.

### 1. Curated 8-Bit Theme Pool (`THEMES` around line 34)
In `src/script.py` (around **line 34**), we define a catalog of specific 8-bit arcade, NES, and Game Boy sprite subjects:
```python
THEMES = [
    "A classic Space Invaders alien crab sprite in bright neon green",
    "Blinky the red Pac-Man ghost with blue eyes on a dark blue background",
    "An 8-bit Princess Peach sprite with golden crown and pink dress",
    ...
]
```
Every 10 minutes, `random.choice(THEMES)` randomly selects one prompt to ensure balanced character representation.

### 2. Direct 8x8 RGB Matrix Prompting & Auto-Centering (around line 150)
In `generate_pixel_art()`, we instruct Gemini to output a structured **8x8 2D array of RGB color triples (`[[[r,g,b], ...], ...]`)** using strict JSON schema mode (`response_mime_type="application/json"`):

```python
    prompt = f"""
You are a master retro video game pixel artist designing authentic {grid_size}x{grid_size} 8-bit sprites.
Generate an iconic {grid_size}x{grid_size} pixel art image array representing: "{theme}".

Output MUST be a valid JSON 2D array containing exactly {grid_size} sub-arrays, each containing exactly {grid_size} RGB lists, structured precisely like this:
[[[r,g,b], [r,g,b], ...], ...]
"""
```

Each 8x8 matrix is centered using `center_pixel_matrix()` and upscaled 2x via `upscale_matrix()` so every single 8-bit pixel becomes a crisp 2x2 LED block on the 16x16 Divoom Timebox Evo grid!

---

## ⚠️ CRITICAL DISCLAIMER: macOS vs. Linux Bluetooth MAC Addresses

When configuring your Bluetooth target address (`DIVOOM_MAC_ADDRESS`), be aware of how different operating systems handle Bluetooth identifiers:

| Operating System | Identifier Format | Example Value | Notes |
| :--- | :--- | :--- | :--- |
| **Linux / Raspberry Pi** | Physical Hardware MAC | `11:75:58:46:FE:3D` | **Required on Raspberry Pi / CasaOS.** Must be a standard 6-byte hexadecimal hardware MAC address. |
| **macOS (Apple)** | CoreBluetooth UUID | `6B3A1398-627A-47C9-FFCD-1A81B7769567` | Apple CoreBluetooth abstracts away real hardware MAC addresses for privacy. |

> [!WARNING]
> **Do not use a macOS CoreBluetooth UUID string (`6B3A1398-...`) on your Raspberry Pi!**  
> If you pass a macOS UUID string to BlueZ on Linux, `Bleak` and `D-Bus` will fail immediately with `FileNotFoundError: [Errno 2] No such file or directory`. Always scan directly on your Raspberry Pi to discover your speaker's physical Linux MAC address (`XX:XX:XX:XX:XX:XX`).

---

## 🍓 Complete Raspberry Pi & CasaOS Setup Guide

### Step 1: Get a Free Google AI Studio API Key
1. Go to **[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** and sign in with your personal Google account.
2. Click **Create API key** -> **Create API key in new project**.
3. Copy your generated key starting with `AIzaSy...`.

---

### Step 2: Find Your Speaker's Linux MAC Address on the Raspberry Pi
Turn on your Divoom Timebox Evo speaker and run this command on your Raspberry Pi SSH terminal:

```bash
sudo hcitool lescan
```

*(Or use our built-in scanner script:* `uv run python src/scan_bluetooth.py --all`*).*  
Look for an entry matching `Timebox-Evo` or `Timebox-Evo-light` and note down its MAC address (e.g., `11:75:58:46:FE:3D`).

---

### Step 3: Deploy on CasaOS via Docker Compose

In your `pixelgrid` project folder on the Raspberry Pi, deploy the container stack using `docker-compose`:

```yaml
services:
  pixelgrid:
    build: .
    container_name: pixelgrid-service
    restart: unless-stopped
    # Host networking & privileged mode required for direct BlueZ access on Linux
    network_mode: "host"
    privileged: true
    volumes:
      - ./downloads:/app/downloads
      # Mandatory Linux D-Bus & SysFS mounts for BlueZ / Bleak operation
      - /var/run/dbus:/var/run/dbus
      - /run/dbus:/run/dbus
      - /sys/class/bluetooth:/sys/class/bluetooth
    environment:
      # Authentication
      - GEMINI_API_KEY=AIzaSyYourNewApiKeyHere
      - GEMINI_MODEL=gemini-2.5-flash
      # Hardware & Scheduling
      - DIVOOM_MAC_ADDRESS=11:75:58:46:FE:3D
      - PORT=8080
      - LOOP_INTERVAL_MINUTES=15
      - PYTHONPATH=/app
```

Launch the service:
```bash
docker-compose up -d --build
```

---

## 🖥️ Running on macOS or Windows

### Why Native Python is Recommended for Bluetooth on Mac/Windows
> [!NOTE]
> **Docker Desktop Limitation on macOS & Windows:** Docker Desktop on macOS and Windows runs Linux containers inside a virtual machine (LinuxKit/WSL2) that **does not support Bluetooth hardware pass-through**. Linux containers running on Docker Desktop for Mac or Windows cannot communicate with host Bluetooth LE adapters.

#### Option A: Native Python with Bluetooth (Recommended for Mac/Windows)
Run PixelGrid directly on your macOS or Windows host OS so `Bleak` can access Apple CoreBluetooth (macOS) or WinRT Bluetooth (Windows) natively:

1. **Install Python dependencies:**
   ```bash
   make setup
   source .venv/bin/activate
   ```
2. **Discover your speaker's address:**
   ```bash
   uv run python src/scan_bluetooth.py --all
   ```
   *(Note: On macOS, this returns an Apple CoreBluetooth UUID like `6B3A1398-627A-47C9-FFCD-1A81B7769567`).*
3. **Start the server natively:**
   ```bash
   export GEMINI_API_KEY=AIzaSyYourApiKeyHere
   export DIVOOM_MAC_ADDRESS=6B3A1398-627A-47C9-FFCD-1A81B7769567
   uv run python src/server.py --port 8080 --interval 15
   ```

#### Option B: Docker Desktop (AI Generation & JSON Archiving Only)
If you run `docker-compose up -d` on macOS or Windows without setting `DIVOOM_MAC_ADDRESS`, the container operates as an **AI Pixel Art Generator**. Every 15 minutes (or via `/refresh`), it generates a new 16x16 pixel art design and archives the JSON files to `./downloads/` without attempting hardware Bluetooth transmission.

---

## 🌐 Webhook Endpoints (`port 8080`)

Once running, PixelGrid exposes an interactive web server on port `8080`:

* **Instant Refresh (`POST /refresh` or `GET /refresh`):**
  Trigger an immediate AI artwork generation and push it to your speaker on-demand:
  ```bash
  curl http://<raspberry-pi-ip>:8080/refresh
  ```
* **Status Diagnostics (`GET /status`):**
  Returns JSON detailing the last generated artwork theme, timestamp, filepath, and BLE status:
  ```bash
  curl http://<raspberry-pi-ip>:8080/status
  ```
* **Health Check (`GET /health`):**
  Returns `200 OK` for container health monitoring.

---

## ⏱️ Periodic Background Scheduler (`LOOP_INTERVAL_MINUTES`)

In addition to the HTTP Webhook API, PixelGrid runs an autonomous asynchronous background scheduler loop inside `src/server.py`.

### How It Works
1. **Automated Cadence:** Controlled by the environment variable `LOOP_INTERVAL_MINUTES` (defaulting to `15` minutes in `docker-compose.yml`). Every 15 minutes, the scheduler automatically wakes up.
2. **Theme Selection:** Selects a high-surprise video game archetype or retro prompt from `THEMES`.
3. **Hardware Wake-Up & Render:** Automatically executes `ensure_bluetooth_ready` on your Raspberry Pi, warms up the Linux BlueZ cache, and transmits the new 16x16 pixel art to your speaker.
4. **Archive Storage:** Every generated artwork JSON file is archived permanently in `/app/downloads/` (`./downloads/` on your host) with a timestamped filename (e.g., `super_mario_2026-07-08_08-30-00.json`).

### Customizing the Cadence
To change how often PixelGrid updates your speaker, edit `LOOP_INTERVAL_MINUTES` in your `docker-compose.yml` (or CasaOS environment settings):
```yaml
environment:
  - LOOP_INTERVAL_MINUTES=30  # Update every 30 minutes (or set to 60 for hourly)
```

---

## 🐳 Docker Operations & Cheat Sheet

Run these commands directly on your Raspberry Pi terminal inside the `pixelgrid` directory:

### 1. Rebuild & Start Container
Whenever you update code or configuration:
```bash
docker-compose up -d --build
```

### 2. View Live Container Logs
Stream real-time logs (generation output, Bluetooth handshakes, and retry attempts):
```bash
docker logs -f pixelgrid-service
```
*(Or view the last 50 lines:* `docker logs --tail 50 pixelgrid-service`*)*

### 3. Scan Bluetooth Devices Inside the Running Container
Verify what BLE devices the running Docker container sees over the air:
```bash
docker exec -it pixelgrid-service python src/scan_bluetooth.py --all
```

### 4. Trigger an Instant Refresh On-Demand
Force a fresh pixel art generation and display update immediately:
```bash
curl http://localhost:8080/refresh
```

---

## 🛠️ Local Development & Testing

1. **Install dependencies using `uv`:**
   ```bash
   make setup
   source .venv/bin/activate
   ```
2. **Run 100% covered unit test suite:**
   ```bash
   make test
   ```
3. **Scan nearby Bluetooth devices:**
   ```bash
   uv run python src/scan_bluetooth.py --all
   ```
