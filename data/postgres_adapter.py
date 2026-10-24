"""
PostgreSQL / Supabase Adapter for Khulaasaa.

Provides seamless compatibility with PostgreSQL (Supabase) using psycopg2:
1. Translates SQLite query syntax (? -> %s, :name -> %(name)s, INSERT OR IGNORE -> ON CONFLICT DO NOTHING).
2. Provides DictCursor results compatible with sqlite3.Row (both key access row['title'] and index row[0]).
3. Manages high-performance thread-safe connection pooling for production deployments.
"""
from __future__ import annotations

import logging
import os
import re
from contextlib import contextmanager
from typing import Any, Generator, Optional
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

logger = logging.getLogger("khulaasaa.postgres")

_POOL: Optional[ThreadedConnectionPool] = None


def get_postgres_url() -> Optional[str]:
    """Retrieve the PostgreSQL / Supabase connection URL from environment."""
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        return None
    
    # Ensure sslmode=require for cloud Supabase if not explicitly configured
    if "supabase." in url and "sslmode" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def is_postgres_configured() -> bool:
    """Return True if a Postgres / Supabase connection URL is configured."""
    return bool(get_postgres_url())


def get_connection_pool() -> ThreadedConnectionPool:
    """Initialize or return the existing connection pool."""
    global _POOL
    if _POOL is None or _POOL.closed:
        url = get_postgres_url()
        if not url:
            raise ValueError("DATABASE_URL or SUPABASE_DB_URL is not configured.")
        minconn = int(os.environ.get("DB_POOL_MIN", "1"))
        maxconn = int(os.environ.get("DB_POOL_MAX", "20"))
        logger.info(f"Initializing PostgreSQL connection pool (min={minconn}, max={maxconn})")
        _POOL = ThreadedConnectionPool(minconn=minconn, maxconn=maxconn, dsn=url)
    return _POOL


def close_connection_pool() -> None:
    """Close all connections in the pool on application shutdown."""
    global _POOL
    if _POOL is not None and not _POOL.closed:
        _POOL.closeall()
        _POOL = None
        logger.info("Closed PostgreSQL connection pool.")


def adapt_sql(sql: str) -> str:
    """
    Adapt SQLite SQL syntax to PostgreSQL / Supabase syntax.
    
    1. Ignores PRAGMA statements.
    2. Converts INSERT OR IGNORE INTO -> INSERT INTO ... ON CONFLICT DO NOTHING.
    3. Converts named parameters :param -> %(param)s.
    4. Converts positional parameters ? -> %s outside string literals.
    """
    s = sql.strip()
    if s.upper().startswith("PRAGMA"):
        return ""

    # INSERT OR IGNORE INTO <table> ... -> INSERT INTO <table> ... ON CONFLICT DO NOTHING;
    if "INSERT OR IGNORE INTO" in s.upper():
        s = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", s, flags=re.IGNORECASE)
        if "ON CONFLICT" not in s.upper():
            s = s.rstrip("; \t\n") + " ON CONFLICT DO NOTHING;"

    # Translate named parameters :param -> %(param)s, avoiding Postgres typecasts like '::jsonb'
    def _repl_named(match: re.Match[str]) -> str:
        prefix = match.group(1)
        name = match.group(2)
        if prefix == ":":
            return match.group(0)  # Typecast, leave untouched
        return f"{prefix}%({name})s"

    s = re.sub(r"(^|[^:])(?::([a-zA-Z_][a-zA-Z0-9_]*))", _repl_named, s)

    # Translate positional ? -> %s outside of single-quoted string literals
    parts: list[str] = []
    in_single_quote = False
    for i, ch in enumerate(s):
        if ch == "'" and (i == 0 or s[i - 1] != "\\"):
            in_single_quote = not in_single_quote
            parts.append(ch)
        elif ch == "?" and not in_single_quote:
            parts.append("%s")
        else:
            parts.append(ch)
    
    return "".join(parts)


class PostgresCursorWrapper:
    """Wrapper around psycopg2 DictCursor providing full sqlite3 cursor parity."""

    def __init__(self, raw_cursor: Any) -> None:
        self._cursor = raw_cursor

    def execute(self, sql: str, params: Optional[Any] = None) -> PostgresCursorWrapper:
        adapted = adapt_sql(sql)
        if not adapted:
            return self
        if params is not None:
            self._cursor.execute(adapted, params)
        else:
            self._cursor.execute(adapted)
        return self

    def executemany(self, sql: str, seq_of_parameters: Any) -> PostgresCursorWrapper:
        adapted = adapt_sql(sql)
        if not adapted:
            return self
        self._cursor.executemany(adapted, seq_of_parameters)
        return self

    def fetchone(self) -> Optional[Any]:
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return self._cursor.fetchall()

    def fetchmany(self, size: Optional[int] = None) -> list[Any]:
        return self._cursor.fetchmany(size) if size is not None else self._cursor.fetchmany()

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    @property
    def description(self) -> Any:
        return self._cursor.description

    @property
    def lastrowid(self) -> Optional[int]:
        return getattr(self._cursor, "lastrowid", None)

    def close(self) -> None:
        self._cursor.close()

    def __iter__(self) -> Any:
        return iter(self._cursor)

    def __enter__(self) -> PostgresCursorWrapper:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


class PostgresConnectionWrapper:
    """Wrapper around psycopg2 connection providing sqlite3.Connection parity."""

    def __init__(self, raw_conn: Any, pool: Optional[ThreadedConnectionPool] = None) -> None:
        self._conn = raw_conn
        self._pool = pool

    def cursor(self) -> PostgresCursorWrapper:
        raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(raw_cur)

    def execute(self, sql: str, params: Optional[Any] = None) -> PostgresCursorWrapper:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.putconn(self._conn)
        else:
            self._conn.close()


@contextmanager
def get_postgres_db() -> Generator[PostgresConnectionWrapper, None, None]:
    """Acquire a pooled Postgres/Supabase connection and yield an adapted wrapper."""
    pool = get_connection_pool()
    raw_conn = pool.getconn()
    conn_wrapper = PostgresConnectionWrapper(raw_conn, pool=pool)
    try:
        yield conn_wrapper
        conn_wrapper.commit()
    except Exception:
        conn_wrapper.rollback()
        raise
    finally:
        conn_wrapper.close()
