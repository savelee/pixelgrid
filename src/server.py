"""HTTP Webhook Server & Periodic Scheduler for PixelGrid.

Runs an async web service on port 8080 allowing on-demand artwork generation
via `/refresh` while running periodic background generation intervals.
"""

import argparse
import asyncio
import logging
import os
from typing import Any

from aiohttp import web

try:
    from src.script import run_once
except ModuleNotFoundError:
    from script import run_once

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("pixelgrid.server")


class PixelGridServer:
    """Async web server and scheduled runner for PixelGrid."""

    def __init__(
        self,
        project_id: str,
        location: str,
        model_name: str,
        download_dir: str,
        mac_address: str | None,
        interval_minutes: int = 10,
        grid_size: int = 8,
    ) -> None:
        """Initializes server settings and runtime state."""
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.download_dir = download_dir
        self.mac_address = mac_address
        self.interval_minutes = interval_minutes
        self.grid_size = grid_size
        self.last_result: dict[str, Any] | None = None
        self._background_task: asyncio.Task[None] | None = None

    async def trigger_generation(self) -> dict[str, Any]:
        """Executes a generation pass and records the result."""
        logger.info("Executing artwork generation pass...")
        result = await run_once(
            project_id=self.project_id,
            location=self.location,
            model_name=self.model_name,
            download_dir=self.download_dir,
            mac_address=self.mac_address,
            grid_size=self.grid_size,
        )
        self.last_result = result
        return result

    async def _periodic_worker(self) -> None:
        """Background worker executing generation on interval."""
        if self.interval_minutes <= 0:
            logger.info("Periodic generation disabled (interval <= 0).")
            return

        logger.info(
            "Periodic background loop started (interval=%d min).",
            self.interval_minutes,
        )
        while True:
            try:
                await asyncio.sleep(self.interval_minutes * 60)
                await self.trigger_generation()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in periodic generation: %s", exc, exc_info=True)

    async def handle_health(self, request: web.Request) -> web.Response:
        """GET /health - Returns service health status."""
        return web.json_response({"status": "ok"})

    async def handle_status(self, request: web.Request) -> web.Response:
        """GET /status - Returns last generation status."""
        return web.json_response(
            {
                "status": "ok",
                "interval_minutes": self.interval_minutes,
                "last_result": self.last_result,
            }
        )

    async def handle_refresh(self, request: web.Request) -> web.Response:
        """GET/POST /refresh - Triggers immediate artwork generation."""
        try:
            result = await self.trigger_generation()
            return web.json_response(
                {
                    "status": "refreshed",
                    "result": result,
                }
            )
        except Exception as exc:
            logger.error("Refresh request failed: %s", exc, exc_info=True)
            return web.json_response(
                {"status": "error", "message": str(exc)}, status=500
            )

    async def on_startup(self, app: web.Application) -> None:
        """Runs initial generation pass and starts background schedule."""
        await self.trigger_generation()
        self._background_task = asyncio.create_task(self._periodic_worker())

    async def on_cleanup(self, app: web.Application) -> None:
        """Cleans up background worker task on shutdown."""
        if self._background_task:
            self._background_task.cancel()
            await asyncio.gather(self._background_task, return_exceptions=True)

    def create_app(self) -> web.Application:
        """Constructs and returns configured aiohttp application."""
        app = web.Application()
        app.add_routes(
            [
                web.get("/health", self.handle_health),
                web.get("/status", self.handle_status),
                web.get("/refresh", self.handle_refresh),
                web.post("/refresh", self.handle_refresh),
            ]
        )
        app.on_startup.append(self.on_startup)
        app.on_cleanup.append(self.on_cleanup)
        return app


def main() -> None:
    """CLI entrypoint for running PixelGrid Webhook Server."""
    parser = argparse.ArgumentParser(description="PixelGrid Webhook Server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8080)),
        help="HTTP server listening port.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("LOOP_INTERVAL_MINUTES", 10)),
        help="Periodic generation interval in minutes.",
    )
    parser.add_argument(
        "--download-dir",
        default=os.environ.get("DOWNLOAD_DIR", "/app/downloads"),
        help="Archive directory for JSON files.",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        default=int(os.environ.get("GRID_SIZE", 8)),
        help="Grid dimension size (default 8).",
    )
    args = parser.parse_args()

    project_id = os.environ.get("GCP_PROJECT_ID", "leeboonstra")
    location = os.environ.get("GEMINI_LOCATION", "global")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    mac_address = os.environ.get("DIVOOM_MAC_ADDRESS")

    server = PixelGridServer(
        project_id=project_id,
        location=location,
        model_name=model_name,
        download_dir=args.download_dir,
        mac_address=mac_address,
        interval_minutes=args.interval,
        grid_size=args.grid_size,
    )
    app = server.create_app()
    web.run_app(app, port=args.port)


if __name__ == "__main__":
    main()
