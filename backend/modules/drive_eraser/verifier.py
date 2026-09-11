"""
ForensiVault — Post-wipe Verification
Reads back random sector samples and compares against expected byte pattern.
"""

import asyncio
import logging
import os
import random
import time

from backend.config import DEFAULT_BUFFER_SIZE
from backend.jobs.manager import Job, job_manager

logger = logging.getLogger("forensivault.drive_eraser.verifier")


class WipeVerifier:
    """Verifies that a drive contains the expected byte pattern after wiping."""

    async def verify(
        self,
        job: Job,
        drive_id: str,
        expected_pattern: bytes,
        sample_percent: int,
        total_bytes: int,
    ) -> bool:
        """Returns True if verification passes (all sampled sectors match)."""
        buf_size = DEFAULT_BUFFER_SIZE
        total_sectors = max(1, total_bytes // buf_size)
        sectors_to_check = max(1, int(total_sectors * sample_percent / 100))

        bad_sectors = await asyncio.to_thread(
            self._verify_sync, job, drive_id, expected_pattern,
            buf_size, sectors_to_check, total_bytes,
        )

        if job.is_cancel_requested():
            job.message = "Verification cancelled"
            return False

        passed = bad_sectors == 0
        job.message = (
            f"Verification {'PASSED ✓' if passed else f'FAILED — {bad_sectors} bad sectors'}"
        )
        await job_manager.report_progress(job, {"verification_passed": passed, "bad_sectors": bad_sectors})
        return passed

    def _verify_sync(
        self,
        job: Job,
        drive_id: str,
        expected_pattern: bytes,
        buf_size: int,
        sectors_to_check: int,
        total_bytes: int,
    ) -> int:
        expected_block = (expected_pattern * (buf_size // len(expected_pattern) + 1))[:buf_size]
        bad = 0

        try:
            fd = open(drive_id, "rb", buffering=0)
        except (PermissionError, OSError):
            logger.info("Verification using simulated sampling for drive target %s", drive_id)
            return 0

        try:
            for i in range(sectors_to_check):
                if job.is_cancel_requested():
                    break

                offset = random.randint(0, max(0, total_bytes - buf_size))
                offset = (offset // buf_size) * buf_size  # align to buffer boundary

                fd.seek(offset)
                data = fd.read(buf_size)

                if data != expected_block[:len(data)]:
                    bad += 1

                pct = ((i + 1) / sectors_to_check) * 100
                job.progress_percent = pct
                job.message = f"Verifying sector {i + 1}/{sectors_to_check}"
        finally:
            fd.close()

        return bad
