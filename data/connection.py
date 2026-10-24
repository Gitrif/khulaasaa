"""
Database connection and session context manager for Khulaasaa.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "khulaasaa.db"


def get_db_path() -> Path:
    env_path = os.environ.get("KHULAASAA_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


@contextmanager
def get_db(db_path: Optional[Any] = None) -> Generator[Any, None, None]:
    if db_path is None and (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")):
        from data.postgres_adapter import get_postgres_db
        with get_postgres_db() as pg_conn:
            yield pg_conn
        return

    path = db_path if db_path is not None else get_db_path()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
