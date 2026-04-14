from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = ROOT_DIR / 'app' / 'data' / 'sessions.sqlite3'
VALID_LOG_LEVELS = {'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'}


def _clean_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _load_env() -> None:
    env_path = ROOT_DIR / '.env'
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), _clean_env_value(value))


_load_env()


def _env_str(name: str, default: str | None = None) -> str | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    return _clean_env_value(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


@dataclass(slots=True)
class Settings:
    gemini_api_key: str | None = None
    gemini_model: str = 'gemini-2.5-flash-lite'
    session_ttl_hours: int = 24
    log_level: str = 'INFO'
    sqlite_path: str = str(DEFAULT_SQLITE_PATH)

    def refresh(self) -> None:
        _load_env()
        self.gemini_api_key = _env_str('GEMINI_API_KEY')
        self.gemini_model = _env_str('GEMINI_MODEL', 'gemini-2.5-flash-lite') or 'gemini-2.5-flash-lite'
        self.session_ttl_hours = _env_int('SESSION_TTL_HOURS', 24)
        self.log_level = (_env_str('LOG_LEVEL', 'INFO') or 'INFO').upper()
        self.sqlite_path = _env_str('SQLITE_PATH', str(DEFAULT_SQLITE_PATH)) or str(DEFAULT_SQLITE_PATH)


settings = Settings()
settings.refresh()


def reload_settings() -> Settings:
    settings.refresh()
    return settings


def validate_settings() -> list[str]:
    errors: list[str] = []

    if not settings.gemini_api_key:
        errors.append('GEMINI_API_KEY is not configured; demo will run with deterministic fallbacks.')

    if settings.session_ttl_hours <= 0:
        errors.append('SESSION_TTL_HOURS must be a positive integer.')

    if settings.log_level.upper() not in VALID_LOG_LEVELS:
        errors.append('LOG_LEVEL must be one of: CRITICAL, ERROR, WARNING, INFO, DEBUG.')

    sqlite_path = Path(settings.sqlite_path)
    if sqlite_path.suffix.lower() not in {'.sqlite3', '.sqlite', '.db'}:
        errors.append('SQLITE_PATH should point to a .sqlite3, .sqlite or .db file.')
    try:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        errors.append(f'SQLITE_PATH parent directory is not writable: {exc}')

    return errors
