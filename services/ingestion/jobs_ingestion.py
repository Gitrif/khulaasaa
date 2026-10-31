"""
Jobs Ingestion Service.
Coordinates job scrapers, persists job records to the database, and dispatches
Telegram and Viber job alerts.
Strictly owns its own database connection lifecycle: scrapers run before acquiring
any database connection; persistence runs in a scoped transaction; alerts run after
persistence finishes with an independent scoped connection.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from typing import Any

from alerts.telegram import dispatch_job_alerts
from data.database import get_db, log_db_error, upsert_job
from scrapers.jobs.gazette import fetch_gazette_job_vacancies
from scrapers.jobs.mycareer import fetch_mycareer_jobs

logger = logging.getLogger("khulaasaa.jobs.ingestion")


def sync_jobs(conn: Any = None, pages: int = 1, trigger_alerts: bool = True) -> dict[str, Any]:
    """Sync recent jobs from Gazette & MyCareer to database and trigger subscriber alerts.

    Performs external network fetches first before acquiring any database connection.
    Alert notifications are dispatched after database persistence completes.
    Owns its database connection lifecycle completely to prevent pool starvation.
    """
    fetched = fetch_gazette_job_vacancies(pages=pages)
    try:
        mycareer_jobs = fetch_mycareer_jobs()
        fetched.extend(mycareer_jobs)
    except Exception as e:
        logger.warning("Error fetching MyCareer jobs: %s", e)

    new_jobs = updated_jobs = alerts_sent = 0
    new_job_records: list[dict[str, Any]] = []

    # 1. Scoped DB write transaction: held only while upserting records
    with get_db() as db_conn:
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
                new_job_records.append(j)
            else:
                updated_jobs += 1
        try:
            db_conn.commit()
        except Exception:
            pass

    # 2. Scoped alert dispatch: executed after persistence connection is fully closed
    if trigger_alerts and new_job_records:
        with get_db() as alert_conn:
            for j in new_job_records:
                notice_id = j["notice_id"]
                try:
                    res = dispatch_job_alerts(j, conn=alert_conn)
                    alerts_sent += res.get("delivered", 0)
                except Exception as exc:
                    log_db_error(logger, f"dispatch_job_alert_{notice_id}", "services.ingestion.jobs_ingestion", exc)
                try:
                    from alerts.viber import dispatch_viber_job_alerts
                    dispatch_viber_job_alerts([j])
                except Exception as exc:
                    log_db_error(logger, f"dispatch_viber_job_{notice_id}", "services.ingestion.jobs_ingestion", exc)

    return {
        "status": "ok",
        "fetched": len(fetched),
        "new": new_jobs,
        "updated": updated_jobs,
        "alerts_sent": alerts_sent,
    }
