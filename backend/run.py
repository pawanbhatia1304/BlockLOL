"""
ForensiVault Backend — Launcher
Run this script with Administrator / Root privileges:

    Windows:  python -m backend.run        (from project root, as Admin)
    Linux:    sudo python -m backend.run

Or directly:
    python backend/run.py
"""

import ctypes
import os
import platform
import sys

# Ensure the project root is on sys.path so `backend.*` imports work
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _check_admin() -> bool:
    if platform.system() == "Windows":
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    return os.geteuid() == 0


def main() -> None:
    if "--mock" in sys.argv:
        os.environ["FORENSIVAULT_MOCK"] = "1"
        print("  [MOCK MODE ENABLED] Simulating low-level disk calls for safe testing.")

    print()
    print("  +==========================================+")
    print("  |      ForensiVault Backend Daemon         |")
    print("  +==========================================+")
    print()

    admin = _check_admin()
    if admin:
        print("  [OK] Running with elevated privileges")
    else:
        print("  [!!] NOT running as Admin/Root.")
        if os.environ.get("FORENSIVAULT_MOCK") == "1":
            print("     Mock mode active: sector progress & carving will be simulated.")
        else:
            print("     Drive-level operations will fail without Admin or --mock.")
            print("     Run with --mock flag for non-destructive UI testing.")
    print()

    # Import after sys.path is set
    from backend.config import HOST, PORT

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
