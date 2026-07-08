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

"""Unit tests for BLE scanner operations."""

from unittest.mock import AsyncMock, patch

import pytest
from src.scan_bluetooth import scan_all_ble_devices, scan_divoom_devices


@pytest.mark.asyncio
async def test_scan_divoom_devices() -> None:
    """Verifies Divoom device scan returns expected tuple list."""
    mock_devices = [("11:75:58:46:FE:3D", "Timebox-Evo")]
    with patch("divoom_protocol.DivoomClient.scan", AsyncMock(return_value=mock_devices)):
        res = await scan_divoom_devices(timeout=1.0)
        assert res == mock_devices


@pytest.mark.asyncio
async def test_scan_all_ble_devices() -> None:
    """Verifies broad BLE scanner returns discovered peripherals."""
    mock_devices = ["Peripheral1", "Peripheral2"]
    with patch("bleak.BleakScanner.discover", AsyncMock(return_value=mock_devices)):
        res = await scan_all_ble_devices(timeout=1.0)
        assert res == mock_devices
