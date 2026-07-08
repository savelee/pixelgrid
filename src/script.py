# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
    # --- SERIES ARCHETYPES (HIGH SURPRISE VALUE) ---
    "A classic Super Mario character or enemy in a dynamic pose",
    "An iconic Pac-Man ghost sprite with expressive pixel eyes in any canonical color",
    "A Legend of Zelda character, enemy, or magical artifact",
    "An iconic Sega character from the Sonic the Hedgehog universe",
    "A classic Capcom or SNK arcade character in an action stance",
    "An iconic 8-bit retro video game boss monster",
    "A retro fighting game character executing a signature special move",
    "A classic RPG character class (wizard, knight, rogue) casting a spell",
    "A cute retro pixel mascot from an 8-bit or 16-bit console era",

    # --- CHARACTERS WITH CREATIVE FREEDOM ---
    "Super Mario or Luigi in an action jumping or power-up pose",
    "A classic Mario enemy (Goomba, Koopa Troopa, Boo, or Piranha Plant)",
    "Link from The Legend of Zelda holding a signature item or weapon",
    "Sonic the Hedgehog or Tails in a fast running or flying pose",
    "Mega Man or one of the classic Robot Masters aiming an arm cannon",
    "Kirby inhaling or wearing a fun copy ability hat",
    "Samus Aran in her Power Suit or a floating Metroid alien creature",
    "Pac-Man navigating a maze with dots or fruit",
    "Simon Belmont or a classic gothic Castlevania monster",
    "Bomberman holding a bomb with a sparking fuse",

    # --- SURPRISE ITEMS, WEAPONS & TREASURES ---
    "A magical fantasy RPG potion bottle with vibrant sparkling liquid",
    "An iconic power-up mushroom, star, or flower from a retro platformer",
    "A glowing legendary sword or shield from a retro adventure game",
    "A retro treasure chest bursting with glowing gems or gold coins",
    "An iconic pixelated heart container or extra-life symbol",
    "A retro gaming console controller, cartridge, or handheld device",

    # --- VEHICLES, MECHS & SPACESHIPS ---
    "A classic retro arcade shoot-'em-up spaceship firing glowing lasers",
    "An alien invader UFO or boss ship from a classic arcade game",
    "A pixelated racing vehicle drifting around a track corner",
    "A retro futuristic mech or combat robot in an 8-bit style",

    # --- ATMOSPHERIC & COZY GAMING SCENES ---
    "A cozy pixelated hearth campfire or glowing fireplace at night",
    "A glowing arcade cabinet in a dark neon-lit game room",
    "A mystical glowing save-point crystal floating above a stone altar",
]


def validate_pixel_matrix(matrix: Any) -> bool:
    """Validates that a JSON payload is a well-formed 16x16 RGB pixel grid.

    Args:
        matrix: The object to validate.

    Returns:
        bool: True if the structure is exactly 16x16 RGB values (0-255).
    """
    if not isinstance(matrix, list) or len(matrix) != 16:
        return False

    for row in matrix:
        if not isinstance(row, list) or len(row) != 16:
            return False
        for pixel in row:
            if not isinstance(pixel, list) or len(pixel) != 3:
                return False
            if not all(
                isinstance(c, int) and 0 <= c <= 255 for c in pixel
            ):
                return False
    return True


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
    project_id: str,
    location: str = "global",
    model_name: str = "gemini-3.5-flash",
    client: genai.Client | None = None,
) -> list[list[list[int]]]:
    """Generates a 16x16 pixel matrix from Vertex AI Gemini.

    Args:
        theme: The subject theme for the artwork.
        project_id: GCP project ID for Vertex AI.
        location: Vertex AI endpoint location (defaults to 'global').
        model_name: Model identifier.
        client: Optional pre-configured genai.Client dependency injection.

    Returns:
        list[list[list[int]]]: Validated 16x16 pixel matrix.

    Raises:
        ValueError: If model output does not conform to the 16x16 schema.
    """
    if client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            logger.info("Authenticating via Google AI Studio API key.")
            client = genai.Client(api_key=api_key)
        else:
            logger.info("Authenticating via Google Cloud Vertex AI ADC.")
            client = genai.Client(
                vertexai=True,
                project=project_id,
                location=location,
            )

    prompt = f"""
You are a master retro video game pixel artist designing vibrant 16x16 LED canvas icons.
Generate a unique, creative 16x16 pixel art image array representing: "{theme}".

Output MUST be a valid JSON 2D array containing exactly 16 sub-arrays, each containing exactly 16 RGB lists, structured precisely like this:
[[[r,g,b], [r,g,b], ...], ...]

ARTISTIC RULES FOR 16x16 LED DISPLAYS:
1. ALWAYS CENTERED: The subject must always be perfectly centered inside the 16x16 grid with balanced margins.
2. ALWAYS HAVE A BACKGROUND: Every image must include a distinct, contrasting background color or atmospheric pattern behind the centered subject (never leave empty black unless black is a deliberate artistic background).
3. COMPOSITION (8-BIT SCALE): Focus on an expressive close-up chibi headshot, bust, or iconic item so signature features remain crisp and legible at 16x16 resolution.
4. COLOR & SHADING (16-BIT DEPTH): Use rich, highly saturated RGB colors with subtle highlights and anti-aliased shading so LEDs glow vibrantly.
5. ICONIC FIDELITY: Strictly preserve canonical character colors.
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
    if not validate_pixel_matrix(matrix):
        raise ValueError(
            "Generated JSON does not match required 16x16 RGB schema."
        )

    return matrix


def ensure_bluetooth_ready() -> None:
    """Ensures Linux Bluetooth controller hci0 is unblocked and powered up."""
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

    ensure_bluetooth_ready()

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
) -> dict[str, Any]:
    """Executes a single generation cycle: Gemini -> JSON -> BLE Display.

    Args:
        project_id: GCP project ID.
        location: Vertex AI endpoint location.
        model_name: Gemini model ID.
        download_dir: Target directory for archived JSON grids.
        mac_address: Optional Bluetooth MAC address.

    Returns:
        dict[str, Any]: Summary result containing theme and output path.
    """
    theme = random.choice(THEMES)
    matrix = generate_pixel_art(
        theme=theme,
        project_id=project_id,
        location=location,
        model_name=model_name,
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
    args = parser.parse_args()

    project_id = os.environ.get("GCP_PROJECT_ID", "leeboonstra")
    location = os.environ.get("GEMINI_LOCATION", "global")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    mac_address = os.environ.get("DIVOOM_MAC_ADDRESS")

    run_kwargs = {
        "project_id": project_id,
        "location": location,
        "model_name": model_name,
        "download_dir": args.download_dir,
        "mac_address": mac_address,
    }

    asyncio.run(run_once(**run_kwargs))


if __name__ == "__main__":
    main()