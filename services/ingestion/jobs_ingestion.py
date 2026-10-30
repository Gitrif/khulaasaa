"""
Jobs Ingestion Service.
Coordinates job scrapers, persists job records to the database, and dispatches
Telegram and Viber job alerts.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any, Optional

from alerts.telegram import dispatch_job_alerts
from data.database import get_db, log_db_error, upsert_job
from scrapers.jobs.gazette import fetch_gazette_job_vacancies
from scrapers.jobs.mycareer import fetch_mycareer_jobs

logger = logging.getLogger("khulaasaa.jobs.ingestion")


def sync_jobs(conn: Optional[Any] = None, pages: int = 1, trigger_alerts: bool = True) -> dict[str, Any]:
    """Sync recent jobs from Gazette & MyCareer to database and trigger subscriber alerts."""
    fetched = fetch_gazette_job_vacancies(pages=pages)
    try:
        mycareer_jobs = fetch_mycareer_jobs()
        fetched.extend(mycareer_jobs)
    except Exception as e:
        logger.warning("Error fetching MyCareer jobs: %s", e)

    new_jobs = updated_jobs = alerts_sent = 0

    def _persist(db_conn):
        nonlocal new_jobs, updated_jobs, alerts_sent
        for j in fetched:
            notice_id = j["notice_id"]
            existing = None
            for attempt in range(4):
                try:
                    db_conn.execute("SAVEPOINT job_sp;")
                    existing = db_conn.execute("SELECT id FROM jobs WHERE notice_id = ?;", (notice_id,)).fetchone()
                    upsert_job(db_conn, j)
                    db_conn.execute("RELEASE SAVEPOINT job_sp;")
                    break
                except sqlite3.OperationalError as op_err:
                    try:
                        db_conn.execute("ROLLBACK TO SAVEPOINT job_sp;")
                    except Exception:
                        pass
                    if "locked" in str(op_err).lower() and attempt < 3:
                        time.sleep(0.3 * (attempt + 1))
                        continue
                    log_db_error(logger, f"process_job_{notice_id}", "services.ingestion.jobs_ingestion", op_err)
                    break
                except Exception as exc:
                    try:
                        db_conn.execute("ROLLBACK TO SAVEPOINT job_sp;")
                    except Exception:
                        pass
                    log_db_error(logger, f"process_job_{notice_id}", "services.ingestion.jobs_ingestion", exc)
                    break

            if existing is None:
                new_jobs += 1
                if trigger_alerts:
                    try:
                        res = dispatch_job_alerts(j, conn=db_conn)
                        alerts_sent += res.get("delivered", 0)
                    except Exception as exc:
                        log_db_error(logger, f"dispatch_job_alert_{notice_id}", "services.ingestion.jobs_ingestion", exc)
                    try:
                        from alerts.viber import dispatch_viber_job_alerts
                        dispatch_viber_job_alerts([j])
                    except Exception as exc:
                        log_db_error(logger, f"dispatch_viber_job_{notice_id}", "services.ingestion.jobs_ingestion", exc)
            else:
                updated_jobs += 1

    if conn is not None:
        _persist(conn)
    else:
        with get_db() as db_conn:
            _persist(db_conn)

    return {
        "status": "ok",
        "fetched": len(fetched),
        "new": new_jobs,
        "updated": updated_jobs,
        "alerts_sent": alerts_sent,
    }
