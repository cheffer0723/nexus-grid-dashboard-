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
            # Privacy-first website analytics: these are aggregate counters only.
            # Do not add IP addresses, user agents, cookies, or visitor IDs here.
            db.execute(
                "CREATE TABLE IF NOT EXISTS analytics_pageviews ("
                "day TEXT NOT NULL, page TEXT NOT NULL, referrer_domain TEXT NOT NULL, "
                "screen_class TEXT NOT NULL, views INTEGER NOT NULL DEFAULT 0, "
                "PRIMARY KEY(day, page, referrer_domain, screen_class))"
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

    def record_pageview(self, day: str, page: str, referrer_domain: str, screen_class: str) -> None:
        """Increment an aggregate counter without retaining a visitor identifier."""
        with self._connect() as db:
            db.execute(
                "INSERT INTO analytics_pageviews(day, page, referrer_domain, screen_class, views) "
                "VALUES(?, ?, ?, ?, 1) "
                "ON CONFLICT(day, page, referrer_domain, screen_class) "
                "DO UPDATE SET views=views+1",
                (day, page, referrer_domain, screen_class),
            )

    def analytics_report(self, days: int) -> dict[str, Any]:
        """Return aggregate web traffic only; no raw events are available."""
        days = max(1, min(days, 365))
        window = f"-{days - 1} days"
        with self._connect() as db:
            total = db.execute(
                "SELECT COALESCE(SUM(views), 0) FROM analytics_pageviews "
                "WHERE day >= date('now', ?)",
                (window,),
            ).fetchone()[0]
            daily = db.execute(
                "SELECT day, SUM(views) AS pageviews FROM analytics_pageviews "
                "WHERE day >= date('now', ?) GROUP BY day ORDER BY day DESC",
                (window,),
            ).fetchall()
            pages = db.execute(
                "SELECT page, SUM(views) AS pageviews FROM analytics_pageviews "
                "WHERE day >= date('now', ?) GROUP BY page ORDER BY pageviews DESC, page ASC LIMIT 20",
                (window,),
            ).fetchall()
            referrers = db.execute(
                "SELECT referrer_domain, SUM(views) AS pageviews FROM analytics_pageviews "
                "WHERE day >= date('now', ?) GROUP BY referrer_domain "
                "ORDER BY pageviews DESC, referrer_domain ASC LIMIT 20",
                (window,),
            ).fetchall()
            screens = db.execute(
                "SELECT screen_class, SUM(views) AS pageviews FROM analytics_pageviews "
                "WHERE day >= date('now', ?) GROUP BY screen_class ORDER BY pageviews DESC, screen_class ASC",
                (window,),
            ).fetchall()
        return {
            "windowDays": days,
            "totalPageviews": int(total),
            "daily": [{"day": row[0], "pageviews": int(row[1])} for row in daily],
            "pages": [{"page": row[0], "pageviews": int(row[1])} for row in pages],
            "referrers": [{"domain": row[0], "pageviews": int(row[1])} for row in referrers],
            "screens": [{"screen": row[0], "pageviews": int(row[1])} for row in screens],
        }
