"""Optional SQLite journal for paper state and the Jev call budget."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class StateStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS events ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, "
                "kind TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS jev_budget (day TEXT PRIMARY KEY, calls INTEGER NOT NULL)"
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA busy_timeout=10000")
        try:
            with db:
                yield db
        finally:
            db.close()

    def load(self) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT value FROM state WHERE key='paper'").fetchone()
        return json.loads(row[0]) if row else None

    def record_cycle(self, snapshot: dict[str, Any], events: list[dict[str, Any]]) -> None:
        payload = json.dumps(snapshot, separators=(",", ":"), allow_nan=False)
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO state(key, value) VALUES('paper', ?)", (payload,))
            db.execute(
                "INSERT INTO events(at, kind, payload) VALUES(?, 'cycle', ?)",
                (snapshot["last_heartbeat"], json.dumps({
                    "cycle": snapshot["cycle"],
                    "signal": snapshot["latest_signal"],
                    "execution": snapshot["latest_execution"],
                    "settings": snapshot["settings"],
                }, separators=(",", ":"), allow_nan=False)),
            )
            for event in events:
                db.execute(
                    "INSERT INTO events(at, kind, payload) VALUES(?, ?, ?)",
                    (event["at"], event["kind"], json.dumps(event, separators=(",", ":"), allow_nan=False)),
                )

    def events(self, kind: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 500))
        with self._connect() as db:
            if kind:
                rows = db.execute(
                    "SELECT id, at, kind, payload FROM events WHERE kind=? ORDER BY id DESC LIMIT ?",
                    (kind, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id, at, kind, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
                ).fetchall()
        return [{"id": row[0], "at": row[1], "kind": row[2], "data": json.loads(row[3])} for row in rows]

    def reserve_jev_call(self, day: str, limit: int) -> bool:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT calls FROM jev_budget WHERE day=?", (day,)).fetchone()
            calls = row[0] if row else 0
            if calls >= limit:
                return False
            db.execute(
                "INSERT INTO jev_budget(day, calls) VALUES(?, ?) "
                "ON CONFLICT(day) DO UPDATE SET calls=excluded.calls",
                (day, calls + 1),
            )
        return True
