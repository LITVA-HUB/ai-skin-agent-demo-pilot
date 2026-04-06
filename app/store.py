from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import RLock

from .config import settings
from .models import SessionState

UTC = timezone.utc


class SessionStore:
    def __init__(self, sqlite_path: str | None = None) -> None:
        self._lock = RLock()
        self._items: dict[str, tuple[datetime, SessionState]] = {}
        self.sqlite_path = Path(sqlite_path or settings.sqlite_path)
        self.backend = 'in-memory'
        self._cleaned_expired = 0
        self._sqlite_enabled = self._init_sqlite()
        if self._sqlite_enabled:
            self.backend = 'sqlite'
            self._cleaned_expired = self.clean_expired()

    def _init_sqlite(self) -> bool:
        try:
            self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.sqlite_path) as connection:
                connection.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        expires_at TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TEXT DEFAULT '',
                        updated_at TEXT DEFAULT ''
                    )
                    '''
                )
                connection.commit()
            return True
        except sqlite3.Error:
            return False

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _expiry(self) -> datetime:
        return datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)

    def save(self, session: SessionState) -> None:
        expires = self._expiry()
        if not self._sqlite_enabled:
            with self._lock:
                self._items[session.session_id] = (expires, session)
            return
        now_iso = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                '''
                INSERT INTO sessions (session_id, expires_at, payload, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    expires_at=excluded.expires_at,
                    payload=excluded.payload,
                    updated_at=excluded.updated_at
                ''',
                (
                    session.session_id,
                    expires.isoformat(),
                    session.model_dump_json(),
                    now_iso,
                    now_iso,
                ),
            )
            connection.commit()

    def get(self, session_id: str) -> SessionState | None:
        if not self._sqlite_enabled:
            with self._lock:
                item = self._items.get(session_id)
                if not item:
                    return None
                expires, session = item
                if expires < datetime.now(UTC):
                    self._items.pop(session_id, None)
                    return None
                return session
        with self._lock, self._connect() as connection:
            row = connection.execute(
                'SELECT expires_at, payload FROM sessions WHERE session_id = ?',
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            expires_at = datetime.fromisoformat(row['expires_at'])
            if expires_at < datetime.now(UTC):
                connection.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
                connection.commit()
                return None
            return SessionState.model_validate_json(row['payload'])

    def clean_expired(self) -> int:
        now_iso = datetime.now(UTC).isoformat()
        if not self._sqlite_enabled:
            with self._lock:
                expired = [session_id for session_id, (expires, _) in self._items.items() if expires < datetime.now(UTC)]
                for session_id in expired:
                    self._items.pop(session_id, None)
                return len(expired)
        with self._lock, self._connect() as connection:
            cursor = connection.execute('DELETE FROM sessions WHERE expires_at < ?', (now_iso,))
            connection.commit()
            return int(cursor.rowcount or 0)

    def session_count(self) -> int:
        if not self._sqlite_enabled:
            with self._lock:
                return len(self._items)
        with self._lock, self._connect() as connection:
            row = connection.execute('SELECT COUNT(*) AS count FROM sessions').fetchone()
            return int(row['count'])

    def stats(self) -> dict[str, object]:
        base: dict[str, object] = {
            'backend': self.backend,
            'sessions': self.session_count(),
        }
        if self._sqlite_enabled:
            base['path'] = str(self.sqlite_path)
            base['cleaned_expired'] = self._cleaned_expired
        return base

    def close(self) -> None:
        return None
