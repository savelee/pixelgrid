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

"""Bluetooth Low Energy (BLE) Scanner for Divoom Displays.

Scans nearby BLE peripherals and identifies Divoom Timebox Evo / Backpack M
displays or lists all visible BLE devices for troubleshooting.
"""

import argparse
import asyncio
import logging
from typing import Any

from bleak import BleakScanner
from divoom_protocol import DivoomClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("scan_bluetooth")


async def scan_divoom_devices(timeout: float = 5.0) -> list[tuple[str, str]]:
    """Scans for peripherals specifically advertising the Divoom UART service.

    Args:
        timeout: Scan duration in seconds.

    Returns:
        list[tuple[str, str]]: List of (address/UUID, name) pairs.
    """
    logger.info("Scanning for Divoom BLE displays (timeout=%.1fs)...", timeout)
    devices = await DivoomClient.scan(timeout=timeout)
    return devices


async def scan_all_ble_devices(timeout: float = 5.0) -> list[Any]:
    """Scans for all BLE peripherals within range.

    Args:
        timeout: Scan duration in seconds.

    Returns:
        list[Any]: List of discovered BLE devices.
    """
    logger.info("Scanning all nearby BLE peripherals (timeout=%.1fs)...", timeout)
    devices = await BleakScanner.discover(timeout=timeout)
    return devices


async def main() -> None:
    """Executes BLE discovery and outputs human-readable summary."""
    parser = argparse.ArgumentParser(description="Divoom BLE Scanner")
    parser.add_argument(
        "--all",
        action="store_true",
        help="List all discovered BLE peripherals in range (not just Divoom).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Scan duration in seconds (default: 5.0)",
    )
    args = parser.parse_args()

    divoom_devices = await scan_divoom_devices(timeout=args.timeout)

    print("\n" + "=" * 60)
    print("                 DIVOOM BLE SCAN RESULTS")
    print("=" * 60)

    if divoom_devices:
        for idx, (addr, name) in enumerate(divoom_devices, start=1):
            print(f"  [{idx}] {name}")
            print(f"      Address / UUID: {addr}")
    else:
        print("  No peripherals advertising Divoom UART service found.")

    if args.all:
        print("\n" + "-" * 60)
        print("              ALL NEARBY BLE PERIPHERALS")
        print("-" * 60)
        all_devices = await scan_all_ble_devices(timeout=args.timeout)
        if all_devices:
            for dev in sorted(
                all_devices, key=lambda d: d.name or "", reverse=True
            ):
                name_str = dev.name or "<Unnamed BLE Peripheral>"
                print(f"  * {name_str:<30} -> {dev.address}")
        else:
            print("  No BLE peripherals detected.")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
