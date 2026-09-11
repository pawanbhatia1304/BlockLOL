"""
ForensiVault — Secure File & Folder Eraser
Multi-pass overwriting with slack-space wiping and metadata scrubbing.
"""

import asyncio
import ctypes
import logging
import os
import random
import string
import subprocess
import time

from backend.config import WIPE_PATTERNS
from backend.jobs.manager import Job, job_manager

logger = logging.getLogger("forensivault.file_eraser")


class SecureFileEraser:
    """Securely erases individual files and directories with cluster-level overwriting."""

    async def erase_files(
        self,
        job: Job,
        paths: list[str],
        method: str,
        wipe_slack: bool,
        scrub_metadata: bool,
    ) -> None:
        target_files: list[str] = []
        target_dirs: list[str] = []

        for p in paths:
            clean_p = p.strip().strip('"').strip("'")
            if not clean_p:
                continue

            abs_p = os.path.abspath(clean_p)
            if os.path.isdir(abs_p):
                target_dirs.append(abs_p)
                for root, _, files in os.walk(abs_p):
                    for f in files:
                        target_files.append(os.path.join(root, f))
            elif os.path.isfile(abs_p):
                target_files.append(abs_p)
            elif os.path.isfile(clean_p):
                target_files.append(os.path.abspath(clean_p))
            else:
                logger.warning("Target file or directory not found: %s", clean_p)
                await job_manager.report_progress(job, {
                    "current_file": clean_p,
                    "message": f"ERROR: Path not found on system: {clean_p}",
                })

        total = len(target_files)
        if total == 0:
            job.message = f"Failed: None of the {len(paths)} specified path(s) exist on local disk."
            job.progress_percent = 100.0
            await job_manager.report_progress(job)
            return

        done = 0
        patterns_list = WIPE_PATTERNS.get(method, [b"\x00"])
        num_passes = len(patterns_list)

        for path in target_files:
            if job.is_cancel_requested():
                break

            job.message = f"Erasing file {done + 1}/{total}: {os.path.basename(path)}"
            await job_manager.report_progress(job, {
                "current_file": path,
                "files_done": done,
                "total_files": total,
            })

            if not os.path.isfile(path):
                done += 1
                continue

            try:
                file_size = os.path.getsize(path)

                # ── Multi-pass overwrite ──
                await asyncio.to_thread(
                    self._overwrite_sync, path, file_size, patterns_list, num_passes
                )

                # ── Slack space ──
                if wipe_slack and not job.is_cancel_requested():
                    await asyncio.to_thread(self._wipe_slack, path, file_size)

                # ── Metadata scrubbing ──
                if scrub_metadata and not job.is_cancel_requested():
                    path = await asyncio.to_thread(self._scrub_metadata, path)

                # ── Physical Delete ──
                if os.path.exists(path):
                    os.remove(path)

                if not os.path.exists(path):
                    logger.info("Securely erased & physically removed: %s", path)
                    await job_manager.report_progress(job, {
                        "message": f"[SUCCESS] Permanently wiped & deleted: {os.path.basename(path)}",
                    })
                else:
                    logger.error("Failed to remove file after wipe: %s", path)

            except PermissionError:
                logger.error("Permission denied: %s — run as Admin/Root", path)
                job.message = f"Permission denied: {path}"
            except Exception as e:
                logger.error("Error erasing %s: %s", path, e)

            done += 1
            job.progress_percent = (done / total) * 100

        # Clean up empty target directories
        import shutil
        for d in target_dirs:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                    logger.info("Removed directory tree: %s", d)
                except Exception as e:
                    logger.warning("Could not remove dir %s: %s", d, e)

        job.message = f"Successfully erased and deleted {done}/{total} files"
        await job_manager.report_progress(job)

    # ── Synchronous helpers (run in thread) ──────────────────

    def _overwrite_sync(
        self, path: str, file_size: int, patterns: list, num_passes: int
    ) -> None:
        for p_idx, pattern in enumerate(patterns):
            with open(path, "rb+") as f:
                f.seek(0)
                written = 0
                while written < file_size:
                    chunk = min(4096, file_size - written)
                    if pattern is None:
                        data = os.urandom(chunk)
                    else:
                        data = (pattern * (chunk // len(pattern) + 1))[:chunk]
                    f.write(data)
                    written += chunk
                f.flush()
                os.fsync(f.fileno())

    def _wipe_slack(self, path: str, file_size: int) -> None:
        """Wipe RAM slack + drive slack by padding to cluster boundary."""
        try:
            if os.name == "nt":
                drive_letter = os.path.splitdrive(path)[0] + "\\"
                spc = ctypes.c_ulong(0)
                bps = ctypes.c_ulong(0)
                fc = ctypes.c_ulong(0)
                tc = ctypes.c_ulong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceW(
                    ctypes.c_wchar_p(drive_letter),
                    ctypes.byref(spc), ctypes.byref(bps),
                    ctypes.byref(fc), ctypes.byref(tc),
                )
                cluster_size = spc.value * bps.value
            else:
                # Linux — default 4096 cluster size
                cluster_size = 4096

            if cluster_size > 0:
                slack = cluster_size - (file_size % cluster_size)
                if 0 < slack < cluster_size:
                    with open(path, "ab") as f:
                        f.write(os.urandom(slack))
                        f.flush()
                        os.fsync(f.fileno())
                    # Truncate back
                    with open(path, "r+b") as f:
                        f.truncate(file_size)
        except Exception as e:
            logger.warning("Slack wipe failed for %s: %s", path, e)

    def _scrub_metadata(self, path: str) -> str:
        """Scrub filesystem metadata by renaming and clearing journal entries."""
        current = path
        try:
            # Windows: attempt USN journal deletion
            if os.name == "nt":
                drive = os.path.splitdrive(path)[0]
                subprocess.run(
                    ["fsutil", "usn", "deletejournal", "/d", drive],
                    capture_output=True, check=False,
                )

            # Rename file multiple times to overwrite directory entries
            directory = os.path.dirname(current)
            for _ in range(3):
                ext = os.path.splitext(current)[1]
                new_name = "".join(random.choices(string.ascii_letters + string.digits, k=16)) + ext
                new_path = os.path.join(directory, new_name)
                os.rename(current, new_path)
                current = new_path

        except Exception as e:
            logger.warning("Metadata scrub incomplete for %s: %s", path, e)

        return current
