"""
Periodic Background Sync Scheduler.
Coordinates background synchronization of News, Tenders, Jobs, and Rentals
without coupling scraper orchestration to the FastAPI application entry point.
Includes thread lifecycle tracking, interruptible waits, and a cross-process
single-instance lock so multi-worker deployments do not run duplicate schedulers.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any, Optional

from services.ingestion.rentals_ingestion import rescrape_and_sync_all_rentals
from services.jobs_service import trigger_jobs_background_sync
from services.news_service import get_live_news
from services.tenders_service import trigger_bids_background_sync

logger = logging.getLogger("khulaasaa.scheduler")

_SHUTDOWN_EVENT = threading.Event()
_SCHEDULER_LOCK = threading.Lock()
_SCHEDULER_THREADS: list[threading.Thread] = []
_SCHEDULER_RUNNING = False
_LOCK_FILE_HANDLE: Optional[Any] = None


def _default_lock_file_path() -> Path:
    custom = os.environ.get("KHULAASAA_SCHEDULER_LOCK_PATH", "").strip()
    if custom:
        return Path(custom)
    return Path(tempfile.gettempdir()) / "khulaasaa_sync_scheduler.lock"


def _acquire_process_lock(lock_path: Optional[Path] = None) -> bool:
    """
    Attempt to acquire a non-blocking cross-process file lock so only one worker
    process runs the background sync scheduler.
    """
    global _LOCK_FILE_HANDLE
    if _LOCK_FILE_HANDLE is not None:
        return True

    target_path = lock_path or _default_lock_file_path()
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(target_path, "a+b")
        fh.seek(0)
        if target_path.stat().st_size == 0:
            fh.write(b"0")
            fh.flush()
            fh.seek(0)

        if os.name == "nt":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        _LOCK_FILE_HANDLE = fh
        return True
    except Exception as exc:
        logger.info("Scheduler process lock already held by another worker (%s); skipping duplicate start.", exc)
        try:
            fh.close()  # type: ignore[has-type]
        except Exception:
            pass
        return False


def _release_process_lock() -> None:
    """Release the cross-process file lock held by this process, if any."""
    global _LOCK_FILE_HANDLE
    fh = _LOCK_FILE_HANDLE
    _LOCK_FILE_HANDLE = None
    if fh is None:
        return
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    finally:
        try:
            fh.close()
        except Exception:
            pass


def _startup_jobs_worker(delay_seconds: float = 3.0) -> None:
    """Wait briefly using an interruptible event before triggering initial jobs background sync."""
    if _SHUTDOWN_EVENT.wait(timeout=delay_seconds):
        return
    try:
        trigger_jobs_background_sync(force=False)
    except Exception as exc:
        logger.warning("Startup jobs trigger failed: %s", exc)


def _periodic_sync_worker(initial_delay: float = 10.0, interval_seconds: float = 180.0) -> None:
    """Background worker that periodically syncs news, tenders, jobs, and rentals with graceful shutdown."""
    if os.environ.get("PYTEST_CURRENT_TEST") and os.environ.get("KHULAASAA_FORCE_SCHEDULER_IN_TESTS") != "1":
        return
    if _SHUTDOWN_EVENT.wait(timeout=initial_delay):
        return

    iteration = 0
    while not _SHUTDOWN_EVENT.is_set():
        iteration += 1

        # News sync every iteration (approx every 3 mins)
        t0 = time.time()
        try:
            get_live_news(force_refresh=True)
            logger.info("Periodic coordinator: news sync scheduled (took %.2fs)", time.time() - t0)
        except Exception as exc:
            logger.warning("Periodic coordinator news sync failed: %s", exc)

        # Tenders sync every 2 iterations (approx every 6 mins)
        if iteration % 2 == 0 and not _SHUTDOWN_EVENT.is_set():
            t0 = time.time()
            try:
                trigger_bids_background_sync(force=True)
                logger.info("Periodic coordinator: tenders sync scheduled (took %.2fs)", time.time() - t0)
            except Exception as exc:
                logger.warning("Periodic coordinator tenders sync failed: %s", exc)

        # Jobs sync on first run and every 5 iterations (approx every 15 mins)
        if (iteration == 1 or iteration % 5 == 0) and not _SHUTDOWN_EVENT.is_set():
            t0 = time.time()
            try:
                trigger_jobs_background_sync(force=True)
                logger.info("Periodic coordinator: jobs sync scheduled (took %.2fs)", time.time() - t0)
            except Exception as exc:
                logger.warning("Periodic coordinator jobs sync failed: %s", exc)

        # Rentals sync on first run and every 20 iterations (approx every 60 mins)
        if (iteration == 1 or iteration % 20 == 0) and not _SHUTDOWN_EVENT.is_set():
            t0 = time.time()
            try:
                cnt = rescrape_and_sync_all_rentals()
                logger.info(
                    "Periodic coordinator: rentals sync completed, %d records synced (took %.2fs)",
                    cnt,
                    time.time() - t0,
                )
            except Exception as exc:
                logger.warning("Periodic coordinator rentals sync failed: %s", exc)

        if _SHUTDOWN_EVENT.wait(timeout=interval_seconds):
            break


def is_scheduler_running() -> bool:
    """Return True if the periodic sync scheduler is currently active in this process."""
    with _SCHEDULER_LOCK:
        return _SCHEDULER_RUNNING and any(t.is_alive() for t in _SCHEDULER_THREADS)


def start_sync_scheduler(
    *,
    startup_jobs_delay: float = 3.0,
    initial_delay: float = 10.0,
    interval_seconds: float = 180.0,
) -> bool:
    """
    Start startup triggers and the periodic synchronization worker thread.
    Returns True if started by this call, or False if disabled, already running,
    or held by another worker process.
    """
    global _SCHEDULER_RUNNING
    if os.environ.get("KHULAASAA_ENABLE_SCHEDULER", "1").strip().lower() in ("0", "false", "no"):
        logger.info("Background sync scheduler disabled via KHULAASAA_ENABLE_SCHEDULER.")
        return False

    with _SCHEDULER_LOCK:
        alive_threads = [t for t in _SCHEDULER_THREADS if t.is_alive()]
        if _SCHEDULER_RUNNING and alive_threads:
            logger.debug("Sync scheduler already running in this process; skipping duplicate start.")
            return False

        if not _acquire_process_lock():
            return False

        _SHUTDOWN_EVENT.clear()
        _SCHEDULER_THREADS.clear()

        try:
            trigger_bids_background_sync(force=False)
        except Exception as exc:
            logger.warning("Startup bids trigger failed: %s", exc)

        jobs_thread = threading.Thread(
            target=_startup_jobs_worker,
            kwargs={"delay_seconds": startup_jobs_delay},
            daemon=True,
            name="StartupJobsTrigger",
        )
        periodic_thread = threading.Thread(
            target=_periodic_sync_worker,
            kwargs={"initial_delay": initial_delay, "interval_seconds": interval_seconds},
            daemon=True,
            name="PeriodicSyncCoordinator",
        )

        _SCHEDULER_THREADS.extend([jobs_thread, periodic_thread])
        _SCHEDULER_RUNNING = True
        jobs_thread.start()
        periodic_thread.start()
        return True


def stop_sync_scheduler(join_timeout: float = 2.0) -> None:
    """Signal all scheduler worker threads to stop, join them with a bounded timeout, and release locks."""
    global _SCHEDULER_RUNNING
    with _SCHEDULER_LOCK:
        _SHUTDOWN_EVENT.set()
        threads_to_join = list(_SCHEDULER_THREADS)
        _SCHEDULER_THREADS.clear()
        _SCHEDULER_RUNNING = False

    for thread in threads_to_join:
        if thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=join_timeout)

    with _SCHEDULER_LOCK:
        _release_process_lock()
