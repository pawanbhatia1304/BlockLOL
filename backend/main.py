"""
ForensiVault Backend — FastAPI Application
Main entry-point: mounts all module routers, WebSocket endpoint,
CORS middleware, and admin privilege checks.
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend import config
from backend.ws.manager import manager as ws_manager

# ── Logging ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-28s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("forensivault")


# ── Admin / Root check ──────────────────────────────────────────

def _is_admin() -> bool:
    """Return True if the process has elevated privileges."""
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def check_admin_permissions() -> bool:
    """Verify elevated privileges, raising HTTP 403 if unprivileged unless MOCK_MODE is enabled."""
    if config.MOCK_MODE:
        return True
    if not _is_admin():
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="ELEVATED PRIVILEGES REQUIRED: Backend must be run as Administrator (Windows) or Root (Linux) to access low-level disk hardware. Pass --mock for testing."
        )
    return True


# ── Lifespan ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    admin = _is_admin()
    logger.info("=" * 60)
    logger.info("  ForensiVault Backend")
    logger.info("  OS        : %s", platform.system())
    logger.info("  Admin     : %s", "YES ✓" if admin else "NO ✗")
    logger.info("  Mock Mode : %s", "ACTIVE ✓" if config.MOCK_MODE else "disabled")
    logger.info("  Host      : %s:%s", config.HOST, config.PORT)
    logger.info("  CORS      : %s", config.CORS_ORIGINS)
    logger.info("  Lighthouse: %s", "configured" if config.LIGHTHOUSE_API_KEY else "not set")
    logger.info("  Blockchain: %s", "configured" if config.CONTRACT_ADDRESS else "not set")
    logger.info("=" * 60)
    if not admin and not config.MOCK_MODE:
        logger.warning(
            "Running without admin privileges. "
            "Drive-level operations will be unavailable. "
            "Restart with 'Run as Administrator' or pass '--mock' for testing."
        )
    yield
    logger.info("ForensiVault Backend shutting down.")


# ── FastAPI App ─────────────────────────────────────────────────

app = FastAPI(
    title="ForensiVault",
    description="Digital Forensics Backend — Secure Erasure, File Carving & Web3 Audit",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the Vite dev server and any configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── WebSocket Endpoint ──────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws_manager.connect(ws)
    try:
        while True:
            # keep the connection alive; client can send pings
            data = await ws.receive_text()
            # echo back acknowledgement
            await ws_manager.send_personal(ws, {"event": "ack", "data": data})
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)
    except Exception:
        await ws_manager.disconnect(ws)


# ── REST Health Check ───────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "admin": _is_admin(),
        "mock_mode": config.MOCK_MODE,
        "os": platform.system(),
        "ws_clients": ws_manager.client_count,
    }


# ── Mount Module Routers ────────────────────────────────────────
# These are imported lazily so the server can start even if a
# module has optional dependencies missing (e.g. wmi on Linux).

def _mount_routers() -> None:
    try:
        from backend.modules.drive_eraser.router import drive_router, wipe_router
        app.include_router(drive_router)
        app.include_router(wipe_router)
        logger.info("Router mounted: drive_eraser")
    except Exception as e:
        logger.warning("Could not mount drive_eraser router: %s", e)

    try:
        from backend.modules.file_eraser.router import router as file_erase_router
        app.include_router(file_erase_router)
        logger.info("Router mounted: file_eraser")
    except Exception as e:
        logger.warning("Could not mount file_eraser router: %s", e)

    try:
        from backend.modules.file_carver.router import router as carve_router
        app.include_router(carve_router)
        logger.info("Router mounted: file_carver")
    except Exception as e:
        logger.warning("Could not mount file_carver router: %s", e)

    try:
        from backend.modules.web3_audit.router import router as audit_router
        app.include_router(audit_router)
        logger.info("Router mounted: web3_audit")
    except Exception as e:
        logger.warning("Could not mount web3_audit router: %s", e)

    # Jobs endpoint
    from backend.jobs.manager import job_manager

    @app.get("/api/jobs")
    async def list_jobs():
        return job_manager.list_all()

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str):
        job = job_manager.get(job_id)
        if not job:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Job not found")
        return job.to_status()


_mount_routers()
