"""16x16 Pixel Art Generator & Divoom Timebox Evo BLE Transmitter.

Generates dynamic 16x16 RGB pixel matrices using Google Cloud Vertex AI Gemini
and transmits them to a Divoom Timebox Evo display over Bluetooth Low Energy.
"""

import argparse
import asyncio
import json
import logging
import os
import random
import subprocess
import sys
from datetime import datetime
from typing import Any

from google import genai
from google.genai import types

try:
    from bleak import BleakScanner
    from divoom_protocol import DivoomClient
except ImportError:
    BleakScanner = None  # type: ignore[assignment,misc]
    DivoomClient = None  # type: ignore[assignment,misc]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pixelgrid")

THEMES = [
    # --- CLASSIC ARCADE 8-BIT SPRITES ---
    "A classic Space Invaders alien crab sprite in bright neon green",
    "Blinky the red Pac-Man ghost with blue eyes on a dark blue background",
    "A Galaga fighter spaceship firing double red lasers upward",
    "Dig Dug character with white helmet and blue suit holding a pump",
    "A classic arcade Pong paddle hitting a square pixel ball",
    "Q*bert orange character standing on an isometric cube tile",
    "Frogger green pixel frog crossing on a dark blue water background",
    "Bubble Bobble green dragon sprite blowing a blue bubble",

    # --- 8-BIT NES & RETRO CONSOLE SPRITES ---
    "An 8-bit Princess Peach sprite with golden crown and pink dress",
    "Mega Man classic blue 8-bit helmet profile on a dark background",
    "An 8-bit Super Mario Super Mushroom (red cap with white spots)",
    "An 8-bit Super Mario jumping sprite in red cap and blue overalls",
    "An 8-bit Bowser green shell with spikes on a dark background",
    "An 8-bit Legend of Zelda golden Triforce glowing on dark royal blue",
    "An 8-bit Link holding a wooden shield and sword",
    "An 8-bit Samus Aran Power Suit orange helmet profile",
    "An 8-bit Goomba walking sprite with brown mushroom cap and white feet",
    "An 8-bit Piranha Plant emerging from a green warp pipe",
    "An 8-bit Boo white ghost with glowing eyes and tongue out",
    "An 8-bit Metroid floating alien larva with green nuclei",
    "An 8-bit Bomberman character with white helmet and pink hands",
    "An 8-bit Donkey Kong brown wooden barrel with white bands",
    "An 8-bit Duck Hunt laughing dog headshot on grass green background",
    "An 8-bit Excitebike red motocross rider jumping on dirt track",
    "An 8-bit Castlevania holy water blue bottle with flame spark",

    # --- RETRO GAMING ICONS & ARTIFACTS ---
    "An 8-bit red and white Poke Ball icon on a dark background",
    "A classic Tetris purple T-block tetromino sprite",
    "An 8-bit Dragon Quest blue Slime monster smiling",
    "An 8-bit Kirby pink round sprite with rosy cheeks",
    "An 8-bit green 1-Up extra life mushroom icon",
    "An 8-bit pixel heart container filled with bright red health",
]



def validate_pixel_matrix(matrix: Any, expected_size: int = 8) -> bool:
    """Validates that a JSON payload is a well-formed square RGB pixel grid.

    Args:
        matrix: The object to validate.
        expected_size: Expected grid width and height (default 8).

    Returns:
        bool: True if the structure is expected_size x expected_size RGB values (0-255).
    """
    if not isinstance(matrix, list) or len(matrix) != expected_size:
        return False

    for row in matrix:
        if not isinstance(row, list) or len(row) != expected_size:
            return False
        for pixel in row:
            if not isinstance(pixel, list) or len(pixel) != 3:
                return False
            if not all(
                isinstance(c, int) and 0 <= c <= 255 for c in pixel
            ):
                return False
    return True


def upscale_matrix(
    matrix: list[list[list[int]]], scale: int = 2
) -> list[list[list[int]]]:
    """Upscales a pixel matrix by repeating each pixel scale x scale times.

    Args:
        matrix: Input 2D RGB pixel list (e.g., 8x8).
        scale: Multiplier factor (default 2 for 8x8 -> 16x16).

    Returns:
        list[list[list[int]]]: Upscaled pixel matrix.
    """
    upscaled: list[list[list[int]]] = []
    for row in matrix:
        scaled_row: list[list[int]] = []
        for pixel in row:
            scaled_row.extend([pixel] * scale)
        for _ in range(scale):
            upscaled.append(list(scaled_row))
    return upscaled


def detect_background_color(matrix: list[list[list[int]]]) -> list[int]:
    """Detects the background RGB color by finding the mode of border pixels.

    Args:
        matrix: 2D list of RGB pixels.

    Returns:
        list[int]: The RGB color list representing the background.
    """
    size = len(matrix)
    border_pixels: list[tuple[int, int, int]] = []
    for r in range(size):
        for c in range(size):
            if r in (0, size - 1) or c in (0, size - 1):
                border_pixels.append((matrix[r][c][0], matrix[r][c][1], matrix[r][c][2]))

    counts: dict[tuple[int, int, int], int] = {}
    for p in border_pixels:
        counts[p] = counts.get(p, 0) + 1

    best_color = max(counts.items(), key=lambda item: item[1])[0]
    return list(best_color)



def center_pixel_matrix(
    matrix: list[list[list[int]]],
) -> list[list[list[int]]]:
    """Centers the foreground bounding box within the square matrix canvas.

    Args:
        matrix: Validated square 2D RGB pixel matrix.

    Returns:
        list[list[list[int]]]: Centered pixel matrix with preserved background.
    """
    size = len(matrix)
    bg = detect_background_color(matrix)

    foreground_coords = [
        (r, c)
        for r in range(size)
        for c in range(size)
        if matrix[r][c] != bg
    ]
    if not foreground_coords:
        return matrix

    min_r = min(r for r, _ in foreground_coords)
    max_r = max(r for r, _ in foreground_coords)
    min_c = min(c for _, c in foreground_coords)
    max_c = max(c for _, c in foreground_coords)

    height = max_r - min_r + 1
    width = max_c - min_c + 1

    target_r = (size - height) // 2
    target_c = (size - width) // 2

    centered = [[bg for _ in range(size)] for _ in range(size)]
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            new_r = target_r + (r - min_r)
            new_c = target_c + (c - min_c)
            if 0 <= new_r < size and 0 <= new_c < size:
                centered[new_r][new_c] = matrix[r][c]
    return centered


def flatten_matrix_to_tuples(
    matrix: list[list[list[int]]],
) -> list[tuple[int, int, int]]:
    """Converts a 16x16 3D pixel list into a flat list of 256 RGB tuples.

    Args:
        matrix: A 16x16 list of [r, g, b] lists.

    Returns:
        list[tuple[int, int, int]]: Flat list of 256 (R, G, B) tuples.
    """
    flat_pixels: list[tuple[int, int, int]] = []
    for row in matrix:
        for pixel in row:
            flat_pixels.append((pixel[0], pixel[1], pixel[2]))
    return flat_pixels


def save_pixel_matrix(
    matrix: list[list[list[int]]],
    download_dir: str,
    theme: str,
    timestamp: datetime | None = None,
) -> str:
    """Saves the generated 16x16 JSON matrix to disk.

    Args:
        matrix: The validated 16x16 RGB pixel array.
        download_dir: Directory where JSON files are archived.
        theme: Chosen artistic theme used to construct the filename.
        timestamp: Optional datetime override for testing.

    Returns:
        str: Absolute filepath of the saved JSON file.
    """
    os.makedirs(download_dir, exist_ok=True)
    ts = (timestamp or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    safe_theme = theme.replace(" ", "_").replace(",", "").lower()
    filepath = os.path.join(download_dir, f"{safe_theme}_{ts}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(matrix, f, indent=2)

    logger.info("Saved pixel grid JSON to %s", filepath)
    return filepath


def generate_pixel_art(
    theme: str,
    project_id: str = "",
    location: str = "global",
    model_name: str = "gemini-2.5-flash",
    client: genai.Client | None = None,
    grid_size: int = 8,
) -> list[list[list[int]]]:
    """Generates a pixel matrix from Google AI Studio Gemini and upscales to 16x16.

    Args:
        theme: The subject theme for the artwork.
        project_id: Ignored (retained for signature compatibility).
        location: Ignored (retained for signature compatibility).
        model_name: Model identifier (defaults to 'gemini-2.5-flash').
        client: Optional pre-configured genai.Client dependency injection.
        grid_size: Base generation grid dimension (default 8 for 8-bit art).

    Returns:
        list[list[list[int]]]: Validated and centered 16x16 pixel matrix.

    Raises:
        ValueError: If model output does not conform to the schema or GEMINI_API_KEY is missing.
    """
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is missing. Please set GEMINI_API_KEY in .env to use Google AI Studio (Free Tier)."
            )
        logger.info("Authenticating via Google AI Studio API key (Free Tier).")
        client = genai.Client(api_key=api_key)


    prompt = f"""
You are a master retro video game pixel artist designing authentic {grid_size}x{grid_size} 8-bit sprites.
Generate an iconic {grid_size}x{grid_size} pixel art image array representing: "{theme}".

Output MUST be a valid JSON 2D array containing exactly {grid_size} sub-arrays, each containing exactly {grid_size} RGB lists, structured precisely like this:
[[[r,g,b], [r,g,b], ...], ...]

ARTISTIC RULES FOR {grid_size}x{grid_size} 8-BIT SPRITES:
1. MAXIMAL CANVAS COVERAGE (NO MINI ICONS): The sprite subject MUST be large, prominent, and fill most of the {grid_size}x{grid_size} canvas (occupying roughly 6x6 or 7x7 active foreground pixels). Do NOT generate tiny or shrunken mini-icons surrounded by empty background.
2. ALWAYS CENTERED: Center the large subject in the middle of the {grid_size}x{grid_size} grid with a clean 1-pixel background border around the edges.
3. SOLID BACKGROUND: Use a clean, contrasting background color behind the sprite. Never leave empty black unless black is a deliberate artistic background.
4. ICONIC 8-BIT FIDELITY: Use bold, highly saturated retro RGB colors. Keep pixel clusters bold and readable at {grid_size}x{grid_size} resolution.
5. STRICT THEME FIDELITY: Strictly depict the exact subject requested in "{theme}". Do not substitute with a different character or item.
"""

    config = types.GenerateContentConfig(
        temperature=1.0,
        top_p=0.95,
        response_mime_type="application/json",
    )

    logger.info("Requesting pixel art generation for theme: '%s'", theme)
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config,
    )

    if not response.text:
        raise ValueError("Empty response returned from Gemini.")

    matrix = json.loads(response.text)
    if not validate_pixel_matrix(matrix, expected_size=grid_size):
        raise ValueError(
            f"Generated JSON does not match required {grid_size}x{grid_size} RGB schema."
        )

    centered_matrix = center_pixel_matrix(matrix)
    if grid_size == 8:
        return upscale_matrix(centered_matrix, scale=2)
    return centered_matrix


def ensure_bluetooth_ready(mac_address: str | None = None) -> None:
    """Ensures Linux Bluetooth controller hci0 is unblocked and stale connections are cleared."""
    if sys.platform.startswith("linux"):
        logger.info("Waking up Linux Bluetooth adapter hci0...")
        try:
            subprocess.run(
                ["rfkill", "unblock", "bluetooth"],
                check=False,
                capture_output=True,
            )
            subprocess.run(
                ["hciconfig", "hci0", "up"],
                check=False,
                capture_output=True,
            )
            if mac_address:
                subprocess.run(
                    ["bluetoothctl", "disconnect", mac_address],
                    check=False,
                    capture_output=True,
                )
        except Exception as err:
            logger.debug("Bluetooth hardware wakeup note: %s", err)


async def push_to_divoom(
    matrix: list[list[list[int]]],
    mac_address: str | None = None,
    brightness: int = 80,
) -> bool:
    """Transmits a 16x16 pixel matrix to a Divoom Timebox Evo over BLE.

    If mac_address is None, attempts to auto-discover a nearby Divoom device.

    Args:
        matrix: Validated 16x16 RGB pixel array.
        mac_address: Optional Bluetooth MAC address or peripheral UUID.
        brightness: LED brightness level (0-100).

    Returns:
        bool: True if transmission succeeded.
    """
    if DivoomClient is None:
        logger.error("divoom-protocol package is not installed.")
        return False

    ensure_bluetooth_ready(mac_address=mac_address)

    target_address = mac_address
    if not target_address:
        logger.info("No MAC address provided; scanning for nearby Divoom BLE devices...")
        devices = await DivoomClient.scan(timeout=5.0)
        if devices:
            target_address, name = devices[0]
            logger.info("Discovered Divoom peripheral via UART service: %s (%s)", name, target_address)
        elif BleakScanner is not None:
            logger.info("No UART service match; scanning BLE names for Timebox/Divoom...")
            all_devices = await BleakScanner.discover(timeout=5.0)
            for dev in all_devices:
                dev_name = (dev.name or "").lower()
                if any(k in dev_name for k in ("timebox", "divoom", "pixoo", "ditoo", "backpack")):
                    target_address = dev.address
                    logger.info("Discovered Divoom peripheral by name: %s (%s)", dev.name, target_address)
                    break

        if not target_address:
            logger.warning("No Divoom BLE peripherals discovered nearby.")
            return False

    flat_pixels = flatten_matrix_to_tuples(matrix)

    if BleakScanner is not None and target_address:
        logger.info("Warming up Linux BlueZ cache for %s...", target_address)
        try:
            await BleakScanner.find_device_by_address(target_address, timeout=10.0)
        except Exception as scan_err:
            logger.debug("Warmup scan info: %s", scan_err)

    for attempt in range(1, 6):
        try:
            logger.info("Connecting to Divoom peripheral at %s (Attempt %d/5)...", target_address, attempt)
            async with DivoomClient() as client:
                await client.connect(target_address)
                await client.init_session()
                await client.set_brightness(brightness)
                await client.static_image(flat_pixels)
            logger.info("Successfully rendered image on Divoom display.")
            return True
        except Exception as exc:
            logger.warning("BLE transmission attempt %d/5 failed: %s", attempt, exc)
            if attempt < 5:
                await asyncio.sleep(2 * attempt)

    logger.error("BLE transmission failed after 5 attempts.")
    return False


async def run_once(
    project_id: str,
    location: str,
    model_name: str,
    download_dir: str,
    mac_address: str | None,
    grid_size: int = 8,
) -> dict[str, Any]:
    """Executes a single generation cycle: Gemini -> JSON -> BLE Display.

    Args:
        project_id: GCP project ID.
        location: Vertex AI endpoint location.
        model_name: Gemini model ID.
        download_dir: Target directory for archived JSON grids.
        mac_address: Optional Bluetooth MAC address.
        grid_size: Generation resolution size (default 8).

    Returns:
        dict[str, Any]: Summary result containing theme and output path.
    """
    theme = random.choice(THEMES)
    matrix = generate_pixel_art(
        theme=theme,
        project_id=project_id,
        location=location,
        model_name=model_name,
        grid_size=grid_size,
    )
    saved_path = save_pixel_matrix(matrix, download_dir, theme)

    pushed_ble = False
    try:
        pushed_ble = await push_to_divoom(matrix, mac_address)
    except Exception as exc:
        logger.error("BLE transmission failed: %s", exc)

    return {
        "theme": theme,
        "json_file": saved_path,
        "ble_transmitted": pushed_ble,
    }



def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="PixelGrid Generator")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single generation pass and exit (default behavior for Supercronic).",
    )
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("DOWNLOAD_DIR", "/app/downloads"),
        help="Directory to archive JSON pixel files.",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=int(os.environ.get("GRID_SIZE", 8)),
        help="Grid dimension size (default 8 for 8-bit sprites).",
    )
    args = parser.parse_args()

    project_id = os.environ.get("GCP_PROJECT_ID")
    location = os.environ.get("GEMINI_LOCATION", "global")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    mac_address = os.environ.get("DIVOOM_MAC_ADDRESS")

    run_kwargs = {
        "project_id": project_id,
        "location": location,
        "model_name": model_name,
        "download_dir": args.download_dir,
        "mac_address": mac_address,
        "grid_size": args.grid_size,
    }

    asyncio.run(run_once(**run_kwargs))


if __name__ == "__main__":
    main()