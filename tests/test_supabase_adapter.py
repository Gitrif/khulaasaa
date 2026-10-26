"""
Tests for Supabase / PostgreSQL Adapter and SQL Translation.
"""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from data.postgres_adapter import (
    adapt_sql,
    get_postgres_url,
    is_postgres_configured,
    PostgresCursorWrapper,
    PostgresConnectionWrapper,
)
from data.supabase_client import is_supabase_configured


def test_adapt_sql_positional_placeholders():
    sql = "SELECT * FROM entities WHERE slug = ? AND entity_type = ?"
    adapted = adapt_sql(sql)
    assert adapted == "SELECT * FROM entities WHERE slug = %s AND entity_type = %s"


def test_adapt_sql_named_placeholders():
    sql = "INSERT INTO bids (notice_id, title) VALUES (:notice_id, :title) ON CONFLICT(notice_id) DO UPDATE SET title = excluded.title RETURNING id;"
    adapted = adapt_sql(sql)
    assert "%(notice_id)s" in adapted
    assert "%(title)s" in adapted
    assert ":notice_id" not in adapted


def test_adapt_sql_preserves_postgres_typecasts():
    sql = "INSERT INTO articles (tags) VALUES (:tags::jsonb)"
    adapted = adapt_sql(sql)
    assert "%(tags)s::jsonb" in adapted


def test_adapt_sql_preserves_question_marks_inside_quotes():
    sql = "SELECT 'Is this a question?' AS q, id FROM users WHERE email = ?"
    adapted = adapt_sql(sql)
    assert "'Is this a question?'" in adapted
    assert "email = %s" in adapted


def test_adapt_sql_escapes_literal_percent_in_strings():
    sql = "DELETE FROM bids WHERE d < ? OR notice_id LIKE 'notice-%';"
    adapted = adapt_sql(sql)
    assert "d < %s" in adapted
    assert "'notice-%%'" in adapted


def test_adapt_sql_insert_or_ignore():
    sql = "INSERT OR IGNORE INTO entities (slug, name_en) VALUES (?, ?);"
    adapted = adapt_sql(sql)
    assert "INSERT INTO entities" in adapted
    assert "ON CONFLICT DO NOTHING" in adapted
    assert "%s, %s" in adapted


def test_adapt_sql_pragmas_stripped():
    assert adapt_sql("PRAGMA foreign_keys = ON;") == ""
    assert adapt_sql("PRAGMA journal_mode = WAL;") == ""
    assert adapt_sql("  pragma busy_timeout = 30000;  ") == ""


def test_get_postgres_url_and_sslmode(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    assert get_postgres_url() is None
    assert is_postgres_configured() is False

    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:secret@db.xyz.supabase.co:5432/postgres")
    url = get_postgres_url()
    assert "sslmode=require" in url
    assert is_postgres_configured() is True


def test_is_supabase_configured(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    assert is_supabase_configured() is False

    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "anon-token")
    assert is_supabase_configured() is True


def test_postgres_cursor_wrapper():
    mock_raw_cursor = MagicMock()
    mock_raw_cursor.fetchone.return_value = {"id": 1, "title": "Test Bid"}
    mock_raw_cursor.fetchall.return_value = [{"id": 1}]
    mock_raw_cursor.rowcount = 1

    wrapper = PostgresCursorWrapper(mock_raw_cursor)
    res = wrapper.execute("SELECT * FROM bids WHERE id = ?", (1,))
    assert res is wrapper
    mock_raw_cursor.execute.assert_called_once_with("SELECT * FROM bids WHERE id = %s", (1,))

    assert wrapper.fetchone() == {"id": 1, "title": "Test Bid"}
    assert wrapper.fetchall() == [{"id": 1}]
    assert wrapper.rowcount == 1


def test_postgres_connection_wrapper():
    mock_raw_conn = MagicMock()
    mock_pool = MagicMock()

    conn_wrapper = PostgresConnectionWrapper(mock_raw_conn, pool=mock_pool)
    conn_wrapper.commit()
    mock_raw_conn.commit.assert_called_once()

    conn_wrapper.rollback()
    mock_raw_conn.rollback.assert_called_once()

    conn_wrapper.close()
    mock_pool.putconn.assert_called_once_with(mock_raw_conn)
