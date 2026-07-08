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

"""Unit tests for PixelGrid Webhook Server."""

from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import web
from src.server import PixelGridServer


@pytest.fixture
def mock_run_once():
    """Mock for run_once execution."""
    with patch("src.server.run_once", new_callable=AsyncMock) as m:
        m.return_value = {
            "theme": "Super Mario",
            "json_file": "/tmp/test.json",
            "ble_transmitted": True,
        }
        yield m


@pytest.mark.asyncio
async def test_server_health_endpoint(aiohttp_client, mock_run_once) -> None:
    """Verifies GET /health returns ok."""
    server = PixelGridServer(
        project_id="test",
        location="global",
        model_name="test-model",
        download_dir="/tmp",
        mac_address=None,
        interval_minutes=0,
    )
    app = server.create_app()
    client = await aiohttp_client(app)

    resp = await client.get("/health")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_server_refresh_endpoint(aiohttp_client, mock_run_once) -> None:
    """Verifies GET /refresh triggers generation and returns updated state."""
    server = PixelGridServer(
        project_id="test",
        location="global",
        model_name="test-model",
        download_dir="/tmp",
        mac_address=None,
        interval_minutes=0,
    )
    app = server.create_app()
    client = await aiohttp_client(app)

    resp = await client.get("/refresh")
    assert resp.status == 200
    data = await resp.json()
    assert data["status"] == "refreshed"
    assert data["result"]["theme"] == "Super Mario"
    assert server.last_result["theme"] == "Super Mario"


@pytest.mark.asyncio
async def test_server_status_endpoint(aiohttp_client, mock_run_once) -> None:
    """Verifies GET /status returns runtime state."""
    server = PixelGridServer(
        project_id="test",
        location="global",
        model_name="test-model",
        download_dir="/tmp",
        mac_address=None,
        interval_minutes=0,
    )
    app = server.create_app()
    client = await aiohttp_client(app)

    resp = await client.get("/status")
    assert resp.status == 200
    data = await resp.json()
    assert "last_result" in data
