"""
Managed Outbox Delivery Worker for Khulaasaa.
Implements the Transactional Outbox Pattern:
1. Asynchronously sweeps 'pending' delivery records persisted during content ingestion.
2. Evaluates and releases 'queued_quiet_hours' when user quiet hours expire.
3. Retries transient failures with bounded exponential backoff.
4. Protects main web threads and ingestion workers from external network latency.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from data.database import get_db
from services.alert_delivery_service import process_operational_delivery_queue

logger = logging.getLogger("khulaasaa.outbox")

_OUTBOX_WORKER: Optional[OutboxWorker] = None
_OUTBOX_LOCK = threading.Lock()


class OutboxWorker:
    """Managed background worker thread for outbox queue processing."""

    def __init__(self, interval_seconds: int = 30) -> None:
        self.interval = max(5, interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def start(self) -> None:
        """Start the outbox worker thread."""
        with _OUTBOX_LOCK:
            if self._is_running:
                return
            self._stop_event.clear()
            self._is_running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="TransactionalOutboxWorker",
            )
            self._thread.start()
            logger.info("Transactional Outbox Worker started (interval=%ds)", self.interval)

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the outbox worker gracefully."""
        with _OUTBOX_LOCK:
            if not self._is_running:
                return
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=timeout)
            self._is_running = False
            logger.info("Transactional Outbox Worker stopped")

    def run_once(self, mock_mode: bool = False) -> dict[str, int]:
        """Execute a single sweep of the outbox delivery queue."""
        try:
            with get_db() as conn:
                return process_operational_delivery_queue(conn, limit=50, mock_mode=mock_mode)
        except Exception as exc:
            logger.warning("Error during outbox worker sweep: %s", exc)
            return {"quiet_hours_released": 0, "dispatched": 0, "failed": 0, "total_attempted": 0}

    def _run_loop(self) -> None:
        """Background loop executing outbox sweeps."""
        while not self._stop_event.is_set():
            self.run_once(mock_mode=False)
            if self._stop_event.wait(timeout=self.interval):
                break


def start_outbox_worker(interval_seconds: int = 30) -> OutboxWorker:
    """Initialize and start the global outbox delivery worker."""
    global _OUTBOX_WORKER
    with _OUTBOX_LOCK:
        if _OUTBOX_WORKER is None:
            _OUTBOX_WORKER = OutboxWorker(interval_seconds=interval_seconds)
        _OUTBOX_WORKER.start()
        return _OUTBOX_WORKER


def stop_outbox_worker() -> None:
    """Stop the global outbox delivery worker."""
    global _OUTBOX_WORKER
    with _OUTBOX_LOCK:
        if _OUTBOX_WORKER is not None:
            _OUTBOX_WORKER.stop()
            _OUTBOX_WORKER = None


def trigger_outbox_sweep(mock_mode: bool = False) -> dict[str, int]:
    """Trigger an immediate outbox sweep on demand (e.g. post-commit)."""
    global _OUTBOX_WORKER
    if _OUTBOX_WORKER:
        return _OUTBOX_WORKER.run_once(mock_mode=mock_mode)
    worker = OutboxWorker()
    return worker.run_once(mock_mode=mock_mode)
