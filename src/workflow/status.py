"""Kernel translation status tracking via kernels/status.json."""

import json
import logging
import threading
from pathlib import Path

log = logging.getLogger("pipeline")


class StatusTracker:
    """Read/write kernel status from kernels/status.json.

    Each kernel entry tracks:
        generated:           bool  - LLM produced output
        compiled:            bool  - passed Zephyr/Spike compilation
        verified:            bool  - passed formal verification (bitwuzla)
        max_verified_batch:  int   - largest batch size verified (0 if not verified)
        attempts:            int   - number of generation/repair attempts
        error:               str   - last error message (if any)

    Autocomp post-verify optimization fields (populated only when --optimize):
        optimized:           bool  - autocomp produced an optimized variant
        optimized_cycles:    int   - measured cycle count for the best candidate
        optimized_verified:  bool  - re-verified against the Phase 1 RVV baseline
        optimized_max_batch: int   - max batch verified for the optimized variant
    """

    def __init__(self, status_file: Path):
        self._path = status_file
        self._data: dict[str, dict] = {}
        self._lock = threading.RLock()   # serialize read-modify-write of status.json under --jobs
        self._load()

    _VALID_FIELDS = {
        "generated", "compiled", "verified",
        "max_verified_batch", "attempts", "error",
        "optimized", "optimized_cycles", "optimized_verified", "optimized_max_batch",
    }

    def _load(self):
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            if not isinstance(raw, dict):
                log.warning("Invalid status.json (expected dict), starting fresh")
                raw = {}
            self._data = raw
            log.info("Loaded status for %d kernels", len(self._data))
        else:
            self._data = {}

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2) + "\n")

    def get(self, kernel: str) -> dict:
        """Get status for a kernel, or empty defaults."""
        return self._data.get(kernel, {
            "generated": False,
            "compiled": False,
            "verified": False,
            "max_verified_batch": 0,
            "attempts": 0,
            "error": "",
            "optimized": False,
            "optimized_cycles": None,
            "optimized_verified": False,
            "optimized_max_batch": 0,
        })

    def update(self, kernel: str, **fields):
        """Update status fields for a kernel and persist.

        Only accepts known fields: generated, compiled, verified, attempts, error.
        Raises ValueError on unknown fields to catch typos early.
        """
        bad = fields.keys() - self._VALID_FIELDS
        if bad:
            raise ValueError(f"Unknown status fields: {bad}. Valid: {self._VALID_FIELDS}")
        with self._lock:
            entry = self.get(kernel)
            entry.update(fields)
            self._data[kernel] = entry
            self._save()

    def is_generated(self, kernel: str) -> bool:
        return self.get(kernel).get("generated", False)

    def is_compiled(self, kernel: str) -> bool:
        return self.get(kernel).get("compiled", False)

    def is_verified(self, kernel: str) -> bool:
        return self.get(kernel).get("verified", False)

    def all_kernels(self) -> dict[str, dict]:
        """Return the full status dict."""
        return dict(self._data)

    def summary(self) -> str:
        """One-line summary of progress."""
        total = len(self._data)
        generated = sum(1 for v in self._data.values() if v.get("generated"))
        compiled = sum(1 for v in self._data.values() if v.get("compiled"))
        verified = sum(1 for v in self._data.values() if v.get("verified"))
        return f"{total} kernels: {generated} generated, {compiled} compiled, {verified} verified"
