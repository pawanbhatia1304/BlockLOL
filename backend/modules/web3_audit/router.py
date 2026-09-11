"""
ForensiVault — Web3 Audit Router
REST endpoints for IPFS upload, blockchain anchoring, and audit log management.
"""

import hashlib
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.config import (
    LIGHTHOUSE_API_KEY,
    BLOCKCHAIN_RPC_URL,
    CONTRACT_ADDRESS,
    PRIVATE_KEY,
    CONTRACT_ABI,
)
from backend.models.schemas import AuditAnchorRequest, AuditRecord
from backend.modules.web3_audit.lighthouse import LighthouseClient
from backend.modules.web3_audit.blockchain import BlockchainClient, LOCAL_LOG_FILE

logger = logging.getLogger("forensivault.web3_audit.router")

router = APIRouter(prefix="/api/audit", tags=["audit"])

# Initialise clients (lazy — they handle missing keys gracefully)
_lighthouse = LighthouseClient(api_key=LIGHTHOUSE_API_KEY)
_blockchain = BlockchainClient(
    rpc_url=BLOCKCHAIN_RPC_URL,
    contract_address=CONTRACT_ADDRESS,
    private_key=PRIVATE_KEY,
    abi=CONTRACT_ABI,
)


@router.post("/anchor")
async def anchor_audit(req: AuditAnchorRequest):
    """
    1. Compute SHA-256 hash of the metadata JSON
    2. Upload to Lighthouse IPFS → get CID
    3. Anchor on blockchain → get tx_hash
    4. Return full AuditRecord
    5. Persist to local JSON log
    """
    # 1. SHA-256
    meta_json = json.dumps(
        {"job_id": req.job_id, "job_type": req.job_type.value, "title": req.title, **req.metadata},
        sort_keys=True,
    )
    data_hash = hashlib.sha256(meta_json.encode("utf-8")).hexdigest()

    # 2. Lighthouse IPFS
    cid = await _lighthouse.upload_json(
        {"job_id": req.job_id, "title": req.title, "hash": data_hash, **req.metadata},
        f"audit_{req.job_id}",
    )

    # 3. Blockchain
    tx_hash = await _blockchain.log_audit_trail(req.job_id, cid, data_hash)

    # 4. Build record
    record = AuditRecord(
        job_id=req.job_id,
        job_type=req.job_type,
        title=req.title,
        ipfs_cid=cid,
        data_hash=data_hash,
        tx_hash=tx_hash,
        metadata=req.metadata,
        blockchain_confirmed=tx_hash not in ("", "local_fallback"),
    )

    # 5. Persist locally
    _save_local(record.model_dump(mode="json"))

    return record.model_dump(mode="json")


@router.get("/verify/{cid}")
async def verify_cid(cid: str):
    """Check if a CID exists on the Lighthouse IPFS gateway."""
    info = await _lighthouse.get_file_info(cid)
    return {"exists": bool(info), "info": info}


@router.get("/logs")
async def get_all_logs():
    """Return all locally-stored audit log entries."""
    return _read_local()


@router.get("/logs/{job_id}")
async def get_log_by_job(job_id: str):
    """Return the audit log entry for a specific job."""
    for entry in _read_local():
        if entry.get("job_id") == job_id:
            return entry
    raise HTTPException(status_code=404, detail="Audit record not found")


# ── Local log helpers ────────────────────────────────────────

def _read_local() -> list[dict[str, Any]]:
    if not os.path.exists(LOCAL_LOG_FILE):
        return []
    try:
        with open(LOCAL_LOG_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error("Error reading local audit log: %s", e)
        return []


def _save_local(record: dict[str, Any]) -> None:
    logs = _read_local()
    logs.append(record)
    try:
        os.makedirs(os.path.dirname(LOCAL_LOG_FILE) or ".", exist_ok=True)
        with open(LOCAL_LOG_FILE, "w") as f:
            json.dump(logs, f, indent=2, default=str)
    except Exception as e:
        logger.error("Error writing local audit log: %s", e)
