# Golden Apple Beauty Advisor (pilot demo)

Локальный FastAPI-прототип AI-консультанта для pilot demo под Golden Apple.

## Current version

- **Archive baseline:** `v0.2.0`
- **Current demo branch snapshot:** `v0.5.1`

Текущее состояние ветки ориентировано на **стабильный demo-сценарий**, а не на production:
- photo-driven старт (анализ фото + первая подборка),
- session-aware follow-up диалог,
- сервер-авторитативная корзина,
- SQLite-backed session storage с in-memory fallback,
- health/ready endpoints с диагностикой конфигурации.

## Architecture

Основные модули:
- `app/main.py` — HTTP API, health/ready, cart endpoints.
- `app/runtime.py` — runtime bootstrap через FastAPI lifespan (store + gemini client).
- `app/store.py` — `SessionStore`: основной backend SQLite, fallback in-memory при ошибке инициализации SQLite.
- `app/logic.py` — orchestration: analyze photo, follow-up intent flow, recommendation refresh.
- `app/intent_service.py`, `app/plan_service.py`, `app/retrieval*.py`, `app/response_service.py` — intent/planning/retrieval/ответ.

### Runtime и storage (фактическая семантика)
- Lifespan runtime используется при запуске приложения; при тестовом/ручном доступе без lifespan включён безопасный lazy-bootstrap.
- `health` и `ready` возвращают фактический backend (`sqlite` или `in-memory`) и список `settings_errors`.
- `production_ready` в `/health` становится `true` только при одновременном выполнении условий:
  1) есть `GEMINI_API_KEY`,
  2) нет `settings_errors`,
  3) storage backend = `sqlite`.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Открыть:
- `http://127.0.0.1:8000/`

Полезные endpoints:
- `GET /health`
- `GET /ready`
- `POST /v1/photo/analyze`
- `POST /v1/session/{session_id}/message`
- cart API:
  - `GET /v1/session/{session_id}/cart`
  - `POST /v1/session/{session_id}/cart/items` (только `sku`; остальные поля берутся сервером из каталога)
  - `PATCH /v1/session/{session_id}/cart/items/{sku}`
  - `DELETE /v1/session/{session_id}/cart/items/{sku}`
  - `DELETE /v1/session/{session_id}/cart`

## Configuration

Приложение читает `.env` из корня репозитория.

Пример (`.env.example`):

```env
GEMINI_API_KEY=replace-me
GEMINI_MODEL=gemini-2.5-flash
SESSION_TTL_HOURS=24
LOG_LEVEL=INFO
SQLITE_PATH=app/data/sessions.sqlite3
```

Назначение переменных:
- `GEMINI_API_KEY` — ключ API Gemini (если отсутствует, работают deterministic fallback paths).
- `GEMINI_MODEL` — имя модели Gemini.
- `SESSION_TTL_HOURS` — TTL сессии в часах.
- `LOG_LEVEL` — уровень логирования (`CRITICAL|ERROR|WARNING|INFO|DEBUG`).
- `SQLITE_PATH` — путь к файлу SQLite для session storage.

## Caveats (честно про demo)

Это **pilot demo**, не production-ready система.

Ограничения:
- каталог synthetic/mock,
- нет real checkout/integration с retail backend,
- нет auth/multi-tenant/per-user persistence,
- ограниченные guardrails LLM (есть grounded fallback, но не полный enterprise safety layer),
- UX и тексты заточены под демонстрацию основного сценария (skincare + complexion, photo → refinement → cart).

## Demo focus

Главный сценарий для показа:
1. Фото пользователя.
2. Стартовая подборка.
3. Follow-up refinement в диалоге.
4. Добавление релевантных SKU в корзину.
