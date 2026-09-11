"""
ForensiVault — File Eraser Router
REST endpoints for secure file/folder deletion.
Supports:
  - /api/file-erase/start   — erase by absolute paths (text input from UI)
  - /api/file-erase/upload  — erase uploaded files (multipart; files land in temp dir then get wiped)
  - /api/file-erase/status  — poll job status
"""

import logging
import os
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import List

from backend.models.schemas import FileEraseRequest, JobType
from backend.jobs.manager import job_manager
from backend.modules.file_eraser.eraser import SecureFileEraser

logger = logging.getLogger("forensivault.file_eraser.router")

router = APIRouter(prefix="/api/file-erase", tags=["file-erase"])


@router.post("/start")
async def start_file_erase(req: FileEraseRequest):
    """Start a secure file erase job by absolute paths."""
    logger.info("FILE-ERASE /start — paths=%s method=%s", req.paths, req.method)
    for i, p in enumerate(req.paths):
        exists = os.path.exists(p.strip())
        abs_p = os.path.abspath(p.strip())
        logger.info("  path[%d]: raw=%r  abs=%r  exists=%s", i, p, abs_p, exists)

    job = job_manager.create(JobType.FILE_ERASE)
    eraser = SecureFileEraser()

    await job_manager.run(
        job,
        eraser.erase_files,
        req.paths,
        req.method,
        req.wipe_slack,
        req.scrub_metadata,
    )

    return {"job_id": job.job_id, "state": job.state.value}


@router.post("/upload")
async def upload_and_erase(
    files: List[UploadFile] = File(...),
    method: str = Form(default="NIST SP 800-88 Clear"),
    wipe_slack: bool = Form(default=True),
    scrub_metadata: bool = Form(default=True),
):
    """
    Accept file uploads, save to a temp directory, then securely wipe & delete them.
    This bypasses the browser path sandboxing issue — files are written to disk on the
    server side and then securely erased from the server's filesystem.
    """
    tmp_dir = tempfile.mkdtemp(prefix="forensivault_erase_")
    saved_paths: list[str] = []

    for upload in files:
        dest = os.path.join(tmp_dir, upload.filename)
        # Avoid path traversal
        dest = os.path.normpath(dest)
        if not dest.startswith(tmp_dir):
            logger.warning("Path traversal attempt blocked: %s", upload.filename)
            continue
        content = await upload.read()
        with open(dest, "wb") as fh:
            fh.write(content)
        saved_paths.append(dest)
        logger.info("Saved uploaded file to temp: %s (%d bytes)", dest, len(content))

    if not saved_paths:
        raise HTTPException(status_code=400, detail="No valid files received for erasure")

    job = job_manager.create(JobType.FILE_ERASE)
    eraser = SecureFileEraser()

    # Also include the temp dir itself so it gets cleaned up
    all_paths = saved_paths + [tmp_dir]

    await job_manager.run(
        job,
        eraser.erase_files,
        all_paths,
        method,
        wipe_slack,
        scrub_metadata,
    )

    return {
        "job_id": job.job_id,
        "state": job.state.value,
        "files_queued": len(saved_paths),
        "file_names": [os.path.basename(p) for p in saved_paths],
    }


@router.get("/status/{job_id}")
async def file_erase_status(job_id: str):
    """Get the current status of a file erase job."""
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_status().model_dump()

