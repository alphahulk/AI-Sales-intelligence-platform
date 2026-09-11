"""Persistent local sales workspace storage."""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

STATUSES = ("New", "Researching", "Qualified", "Contacted", "Meeting booked", "Disqualified")

POSTGRES_SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_accounts (
    domain TEXT PRIMARY KEY,
    saved_at TEXT NOT NULL,
    owner TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT NOT NULL DEFAULT '',
    next_action TEXT NOT NULL DEFAULT '',
    next_action_date TEXT NOT NULL DEFAULT ''
)
"""


def postgres_enabled() -> bool:
    return bool(os.getenv("DATABASE_URL"))


def postgres_connection():
    import psycopg

    connection = psycopg.connect(os.environ["DATABASE_URL"])
    connection.execute(POSTGRES_SCHEMA)
    connection.commit()
    return connection


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_accounts (
            domain TEXT PRIMARY KEY,
            saved_at TEXT NOT NULL,
            owner TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'New',
            notes TEXT NOT NULL DEFAULT '',
            next_action TEXT NOT NULL DEFAULT '',
            next_action_date TEXT NOT NULL DEFAULT ''
        )
        """
    )
    connection.commit()
    return connection


def save_account(path: Path, domain: str) -> None:
    if postgres_enabled():
        connection = postgres_connection()
        try:
            connection.execute(
                "INSERT INTO saved_accounts (domain, saved_at) VALUES (%s, %s) ON CONFLICT (domain) DO NOTHING",
                (domain, datetime.now(timezone.utc).isoformat()),
            )
            connection.commit()
        finally:
            connection.close()
        return
    connection = connect(path)
    try:
        connection.execute(
            "INSERT OR IGNORE INTO saved_accounts (domain, saved_at) VALUES (?, ?)",
            (domain, datetime.now(timezone.utc).isoformat()),
        )
        connection.commit()
    finally:
        connection.close()


def remove_account(path: Path, domain: str) -> None:
    if postgres_enabled():
        connection = postgres_connection()
        try:
            connection.execute("DELETE FROM saved_accounts WHERE domain = %s", (domain,))
            connection.commit()
        finally:
            connection.close()
        return
    connection = connect(path)
    try:
        connection.execute("DELETE FROM saved_accounts WHERE domain = ?", (domain,))
        connection.commit()
    finally:
        connection.close()


def list_accounts(path: Path) -> list[dict]:
    if postgres_enabled():
        connection = postgres_connection()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT domain, saved_at, owner, status, notes, next_action, next_action_date FROM saved_accounts ORDER BY saved_at DESC")
                columns = [item.name for item in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()
    connection = connect(path)
    try:
        return [dict(row) for row in connection.execute("SELECT * FROM saved_accounts ORDER BY saved_at DESC")]
    finally:
        connection.close()


def update_account(path: Path, domain: str, owner: str, status: str, notes: str, next_action: str, next_action_date: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Unsupported status: {status}")
    if postgres_enabled():
        connection = postgres_connection()
        try:
            connection.execute(
                "UPDATE saved_accounts SET owner = %s, status = %s, notes = %s, next_action = %s, next_action_date = %s WHERE domain = %s",
                (owner, status, notes, next_action, next_action_date, domain),
            )
            connection.commit()
        finally:
            connection.close()
        return
    connection = connect(path)
    try:
        connection.execute(
            """
            UPDATE saved_accounts
            SET owner = ?, status = ?, notes = ?, next_action = ?, next_action_date = ?
            WHERE domain = ?
            """,
            (owner, status, notes, next_action, next_action_date, domain),
        )
        connection.commit()
    finally:
        connection.close()
