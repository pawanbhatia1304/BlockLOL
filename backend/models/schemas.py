"""
ForensiVault Backend — Pydantic Models
Shared request / response schemas for all API endpoints.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ──────────────────────────────────────────────────────

class JobType(str, enum.Enum):
    WIPE = "wipe"
    FILE_ERASE = "file_erase"
    CARVE = "carve"


class JobState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ─── Drive Detection ────────────────────────────────────────────

class PartitionInfo(BaseModel):
    name: str = ""
    mount_point: str = ""
    file_system: str = ""
    size_bytes: int = 0
    used_bytes: int = 0


class DriveInfo(BaseModel):
    device_id: str                      # e.g. "\\.\PhysicalDrive0" or "/dev/sda"
    model: str = "Unknown"
    serial: str = ""
    size_bytes: int = 0
    interface_type: str = ""            # SCSI, NVMe, USB, etc.
    media_type: str = ""                # HDD, SSD, Removable
    sector_size: int = 512
    partitions: list[PartitionInfo] = []
    is_system_disk: bool = False
    health_status: str = "Good (SMART Passed)"


# ─── Wipe ────────────────────────────────────────────────────────

class WipeRequest(BaseModel):
    drive_id: str
    method: str = "NIST SP 800-88 Clear"
    verify: bool = True
    verification_percent: int = Field(default=5, ge=1, le=100)
    confirm_system_wipe: bool = False


class WipeProgress(BaseModel):
    job_id: str
    state: JobState
    current_pass: int = 0
    total_passes: int = 1
    bytes_written: int = 0
    total_bytes: int = 0
    speed_mbps: float = 0.0
    progress_percent: float = 0.0
    message: str = ""
    verification_passed: Optional[bool] = None


# ─── File Erase ──────────────────────────────────────────────────

class FileEraseRequest(BaseModel):
    paths: list[str]
    method: str = "NIST SP 800-88 Clear"
    wipe_slack: bool = True
    scrub_metadata: bool = True


class FileEraseProgress(BaseModel):
    job_id: str
    state: JobState
    current_file: str = ""
    files_done: int = 0
    total_files: int = 0
    progress_percent: float = 0.0
    message: str = ""


# ─── File Carving ────────────────────────────────────────────────

class CarveRequest(BaseModel):
    source: str                          # drive path or image file path
    file_types: list[str] = []           # empty = all types
    scan_depth: str = "deep"             # "deep", "metadata", "targeted"


class RecoveredFile(BaseModel):
    file_id: str
    file_name: str
    file_type: str
    size_bytes: int = 0
    offset: int = 0                      # byte offset on source
    confidence: float = 0.0              # 0–100%
    entropy: float = 0.0
    output_path: str = ""
    header_hex: str = ""


class CarveProgress(BaseModel):
    job_id: str
    state: JobState
    bytes_scanned: int = 0
    total_bytes: int = 0
    progress_percent: float = 0.0
    files_found: int = 0
    speed_mbps: float = 0.0
    message: str = ""


class CarveResult(BaseModel):
    job_id: str
    source: str
    duration_seconds: float = 0.0
    total_bytes_scanned: int = 0
    files_recovered: list[RecoveredFile] = []


# ─── Web3 / Audit ───────────────────────────────────────────────

class AuditAnchorRequest(BaseModel):
    job_id: str
    job_type: JobType
    title: str
    metadata: dict[str, Any] = {}


class AuditRecord(BaseModel):
    job_id: str
    job_type: JobType
    title: str
    ipfs_cid: str = ""
    data_hash: str = ""
    tx_hash: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = {}
    blockchain_confirmed: bool = False


# ─── Job Status ──────────────────────────────────────────────────

class JobStatus(BaseModel):
    job_id: str
    job_type: JobType
    state: JobState
    created_at: datetime
    updated_at: datetime
    progress_percent: float = 0.0
    message: str = ""
    result: Optional[dict[str, Any]] = None


# ─── WebSocket Messages ─────────────────────────────────────────

class WSMessage(BaseModel):
    """Envelope for all WebSocket messages from server → client."""
    event: str                           # "progress", "drive_list", "job_complete", "error"
    job_id: str = ""
    data: dict[str, Any] = {}
