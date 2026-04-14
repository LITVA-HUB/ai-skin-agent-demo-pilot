from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import reload_settings, settings, validate_settings
from .gemini_client import GeminiClient
from .observability import log_event, log_warning
from .store import SessionStore


def build_runtime() -> tuple[SessionStore, GeminiClient]:
    reload_settings()
    return SessionStore(), GeminiClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    reload_settings()
    settings_errors = validate_settings()
    if settings_errors:
        for error in settings_errors:
            log_warning('startup_config_warning', message=error)
    store, gemini = build_runtime()
    gemini_available = False
    if gemini.api_key:
        gemini_available = await gemini.ping()
    app.state.store = store
    app.state.gemini = gemini
    app.state.settings_errors = settings_errors
    log_event(
        'startup',
        version=app.version,
        storage=store.stats(),
        gemini_configured=bool(gemini.api_key),
        gemini_available=gemini_available,
        gemini_model=gemini.active_model,
        gemini_last_error=gemini.last_error,
        sqlite_path=settings.sqlite_path,
        settings_errors=settings_errors,
    )
    try:
        yield
    finally:
        store.close()
        log_event('shutdown', version=app.version)
