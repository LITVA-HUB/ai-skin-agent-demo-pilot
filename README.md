# Golden Apple Beauty Advisor (pilot demo)

Локальный FastAPI-прототип AI-консультанта для pilot demo под Golden Apple.

## Current version

- **Archive baseline:** `v0.2.0`
- **Current demo branch snapshot:** `v0.6.0`

Текущее состояние ветки ориентировано на **стабильный demo-сценарий guided choice**, а не на production:
- camera/photo-driven старт (живой scan shell + анализ фото + первая подборка),
- session-aware follow-up диалог с conversational advisor,
- быстрые quick actions для управляемого refinement (`дешевле / сияющий / вечер / натуральнее / халяль`),
- сервер-авторитативная корзина с добавлением, уменьшением количества и удалением позиций,
- отдельные `Advisor` / `Cabinet` / `Cart` сценарии в одной demo-flow,
- OpenRouter-backed live LLM path с grounded fallback,
- SQLite-backed session storage с in-memory fallback,
- health/ready endpoints с диагностикой конфигурации.

## Demo snapshot: what already works

Сейчас в демке уже есть цельный путь:

1. `Scan`
- запуск с камеры или по фото,
- аккуратный face-frame и guided state machine,
- переход в результат и advisor без отдельного “технического” экрана.

2. `Advisor`
- стартовое explanation после scan,
- чат с короткими follow-up сообщениями,
- быстрые refinement-actions прямо в диалоге,
- curated recommendations под текущий сценарий.

3. `Recommendations`
- hero product + supporting products,
- why-text на карточках,
- add/open actions,
- связка с текущим intent пользователя.

4. `Cart`
- добавление из набора,
- `+` / `−` по количеству,
- полное удаление позиции,
- subtotal / count / demo checkout.

5. `Cabinet`
- профиль и краткий beauty summary,
- история анализов,
- история demo-заказов.

## Recommended demo flow

Если показывать проект как pilot demo, сейчас лучше всего работает такой сценарий:

1. открыть `Scan`,
2. сделать фото или быстрый camera scan,
3. открыть `Advisor`,
4. сделать 1-2 уточнения через quick actions или короткое сообщение,
5. добавить товары в корзину,
6. показать `Cabinet` и историю.

### Что рекомендую использовать на показе

- **LLM provider:** `openrouter`
- **Model:** `google/gemini-3.1-flash-lite-preview`
- **Storage:** `sqlite`
- **Run mode:** локально через `python -m app`

Это сейчас самый стабильный demo-режим для “живого” advisor без лишней возни.

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
python -m app
```

Открыть:
- `http://127.0.0.1:8010/`
- `http://localhost:8010/`

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
LLM_PROVIDER=openrouter
GEMINI_API_KEY=replace-me
GEMINI_MODEL=gemini-3.1-flash-lite-preview
OPENROUTER_API_KEY=replace-me
OPENROUTER_MODEL=google/gemini-3.1-flash-lite-preview
OPENROUTER_SITE_URL=http://127.0.0.1:8010
OPENROUTER_APP_NAME=Golden Apple Beauty ID Demo
SESSION_TTL_HOURS=24
LOG_LEVEL=INFO
SQLITE_PATH=app/data/sessions.sqlite3
```

Назначение переменных:
- `LLM_PROVIDER` — активный live-провайдер (`gemini` или `openrouter`).
- `GEMINI_API_KEY` — ключ API Gemini (если отсутствует, работают deterministic fallback paths).
- `GEMINI_MODEL` — имя модели Gemini.
- `OPENROUTER_API_KEY` — ключ OpenRouter для OpenAI-совместимого `/chat/completions`.
- `OPENROUTER_MODEL` — модель в OpenRouter, например `google/gemini-3.1-flash-lite-preview`.
- `OPENROUTER_SITE_URL` / `OPENROUTER_APP_NAME` — необязательные OpenRouter headers для referer/title.
- `SESSION_TTL_HOURS` — TTL сессии в часах.
- `LOG_LEVEL` — уровень логирования (`CRITICAL|ERROR|WARNING|INFO|DEBUG`).
- `SQLITE_PATH` — путь к файлу SQLite для session storage.

## Release notes for `v0.6.0`

Что отличает этот snapshot от более ранних веток:

- advisor стал более conversational и меньше похож на scripted demo bot,
- стартовое сообщение после scan стало понятнее и ближе к живому консультанту,
- quick actions перестали ломать основной goal и домен запроса,
- OpenRouter path работает как основной live-provider,
- корзина теперь поддерживает не только добавление, но и уменьшение количества / удаление товара,
- UI scan/advisor flow стабилизирован после отката неудачного experimental scanner-pass.

## Caveats (честно про demo)

Это **pilot demo AI beauty advisor**, не medical-диагностика и не production-ready система.

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
