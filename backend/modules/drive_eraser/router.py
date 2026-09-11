"""
ForensiVault — Drive Eraser Routers
REST endpoints for drive detection and secure wipe operations.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.models.schemas import WipeRequest, JobType
from backend.jobs.manager import job_manager
from backend.modules.drive_eraser.detector import DriveDetector
from backend.modules.drive_eraser.eraser import DriveEraser

logger = logging.getLogger("forensivault.drive_eraser.router")

drive_router = APIRouter(prefix="/api/drives", tags=["drives"])
wipe_router = APIRouter(prefix="/api/wipe", tags=["wipe"])


@drive_router.get("/list")
async def list_drives():
    """Enumerate all connected physical drives."""
    detector = DriveDetector()
    drives = await detector.list_drives()
    return [d.model_dump() for d in drives]


@wipe_router.post("/start")
async def start_wipe(req: WipeRequest):
    """Start a secure drive wipe job in the background."""
    # Safety Check: Prevent accidental destruction of OS system partition
    detector = DriveDetector()
    drives = await detector.list_drives()
    target_drive = next((d for d in drives if d.device_id == req.drive_id), None)
    
    if target_drive and target_drive.is_system_disk and not req.confirm_system_wipe:
        raise HTTPException(
            status_code=400,
            detail="SYSTEM DRIVE PROTECTION: Targeted drive is an OS system disk. You must pass 'confirm_system_wipe: true' to confirm destructive wiping."
        )

    job = job_manager.create(JobType.WIPE)
    eraser = DriveEraser()

    await job_manager.run(
        job,
        eraser.wipe,
        req.drive_id,
        req.method,
        req.verify,
        req.verification_percent,
    )

    return {"job_id": job.job_id, "state": job.state.value}


@wipe_router.get("/status/{job_id}")
async def wipe_status(job_id: str):
    """Get the current status of a wipe job."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_status().model_dump()


@wipe_router.post("/cancel/{job_id}")
async def cancel_wipe(job_id: str):
    """Request cancellation of a running wipe job."""
    ok = await job_manager.cancel(job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    return {"message": "Cancellation requested", "job_id": job_id}
