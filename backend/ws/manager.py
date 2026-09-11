"""
ForensiVault Backend — WebSocket Connection Manager
Manages connected WebSocket clients and broadcasts real-time
progress updates for wipe / carve / erase jobs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger("forensivault.ws")


class ConnectionManager:
    """
    Thread-safe WebSocket hub.

    • Accepts new client connections
    • Removes disconnected clients
    • Broadcasts JSON messages to all connected clients
    • Supports per-job subscriptions (optional filtering)
    """

    def __init__(self) -> None:
        self._active: list[WebSocket] = []
        self._lock = asyncio.Lock()

    # ── lifecycle ────────────────────────────────────────────

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._active.append(ws)
        logger.info("WS client connected  (%d total)", len(self._active))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._active:
                self._active.remove(ws)
        logger.info("WS client disconnected (%d remain)", len(self._active))

    # ── messaging ────────────────────────────────────────────

    async def send_personal(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to one client."""
        try:
            await ws.send_text(json.dumps(message, default=str))
        except Exception:
            await self.disconnect(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to every connected client."""
        payload = json.dumps(message, default=str)
        async with self._lock:
            stale: list[WebSocket] = []
            for ws in self._active:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._active.remove(ws)

    async def broadcast_progress(
        self,
        event: str,
        job_id: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Convenience wrapper — sends a progress envelope."""
        await self.broadcast({
            "event": event,
            "job_id": job_id,
            "data": data or {},
        })

    @property
    def client_count(self) -> int:
        return len(self._active)


# Singleton shared across all routers
manager = ConnectionManager()
