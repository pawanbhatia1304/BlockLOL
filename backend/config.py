"""
ForensiVault Backend — Configuration
Loads settings from environment variables / .env file.
"""

import os
import platform
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")


# ── OS Detection ──────────────────────────────────────────────
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# ── Server ────────────────────────────────────────────────────
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
MOCK_MODE = os.getenv("FORENSIVAULT_MOCK", "0").lower() in ("1", "true", "yes")

# ── Lighthouse (IPFS) ────────────────────────────────────────
LIGHTHOUSE_API_KEY = os.getenv("LIGHTHOUSE_API_KEY", "")

# ── Blockchain ────────────────────────────────────────────────
BLOCKCHAIN_RPC_URL = os.getenv("BLOCKCHAIN_RPC_URL", "https://rpc-amoy.polygon.technology")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS", "")
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")

# ── Wipe defaults ─────────────────────────────────────────────
DEFAULT_BUFFER_SIZE = 1024 * 1024          # 1 MB per write chunk
VERIFICATION_SAMPLE_PERCENT = 5            # 5% statistical sample
WIPE_PATTERNS = {
    "NIST SP 800-88 Clear": [b"\x00"],
    "DoD 5220.22-M (3 pass)": [b"\x00", b"\xff", None],   # None = random
    "Random data (7 pass)": [None] * 7,
    "Cryptographic erase": [None],
}

# ── File carving ──────────────────────────────────────────────
CARVE_OUTPUT_DIR = Path(os.getenv("CARVE_OUTPUT_DIR", str(_backend_dir / "carved_files")))
CARVE_BUFFER_SIZE = 4 * 1024 * 1024       # 4 MB streaming buffer
MAX_CARVE_WORKERS = 4

# ── Smart-contract ABI (minimal for logAuditTrail) ────────────
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "jobId", "type": "string"},
            {"internalType": "string", "name": "ipfsCid", "type": "string"},
            {"internalType": "string", "name": "dataHash", "type": "string"},
        ],
        "name": "logAuditTrail",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "string", "name": "jobId", "type": "string"},
        ],
        "name": "getAuditTrail",
        "outputs": [
            {"internalType": "string", "name": "ipfsCid", "type": "string"},
            {"internalType": "string", "name": "dataHash", "type": "string"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "string", "name": "jobId", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "ipfsCid", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "dataHash", "type": "string"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "AuditTrailLogged",
        "type": "event",
    },
]
