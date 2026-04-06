from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from .catalog import load_catalog
from .logic import analyze_photo, handle_message
from .models import AnalyzePhotoRequest, AnalyzePhotoResponse, CartItem, CartResponse, SessionMessageRequest, SessionMessageResponse, SessionState, UpdateCartItemRequest, AddCartItemRequest
from .observability import log_error
from .runtime import lifespan, build_runtime
from .config import validate_settings

APP_VERSION = '0.5.1'
app = FastAPI(title='Golden Apple Beauty Advisor', version=APP_VERSION, lifespan=lifespan)
TEMPLATE_DIR = Path(__file__).parent / 'templates'


def _ensure_runtime(request: Request) -> None:
    if hasattr(request.app.state, 'store') and hasattr(request.app.state, 'gemini'):
        return
    store, gemini = build_runtime()
    request.app.state.store = store
    request.app.state.gemini = gemini
    request.app.state.settings_errors = validate_settings()


def _store(request: Request):
    _ensure_runtime(request)
    return request.app.state.store


def _gemini(request: Request):
    _ensure_runtime(request)
    return request.app.state.gemini


def _settings_errors(request: Request) -> list[str]:
    _ensure_runtime(request)
    return list(getattr(request.app.state, 'settings_errors', []))


def _cart_response(session: SessionState) -> CartResponse:
    return CartResponse(cart=session.cart, total_items=session.cart.total_items, total_price=session.cart.total_price)


def _catalog_item_by_sku(sku: str):
    return next((product for product in load_catalog() if product.sku == sku), None)


@app.get('/', response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((TEMPLATE_DIR / 'index.html').read_text(encoding='utf-8'))


@app.get('/health')
def health(request: Request) -> dict[str, object]:
    store = _store(request)
    gemini = _gemini(request)
    settings_errors = _settings_errors(request)
    store_stats = store.stats()
    return {
        'status': 'ok',
        'version': request.app.version,
        'storage': store_stats.get('backend', 'in-memory'),
        'gemini_configured': bool(gemini.api_key),
        'gemini_model': gemini.model,
        'settings_errors': settings_errors,
        'production_ready': bool(gemini.api_key) and not settings_errors and store_stats.get('backend') == 'sqlite',
    }


@app.get('/ready')
def ready(request: Request) -> dict[str, object]:
    store = _store(request)
    gemini = _gemini(request)
    return {
        'status': 'ready',
        'version': request.app.version,
        'store': store.stats(),
        'gemini_configured': bool(gemini.api_key),
        'settings_errors': _settings_errors(request),
    }


@app.post('/v1/photo/analyze', response_model=AnalyzePhotoResponse)
async def analyze_photo_endpoint(request: Request, payload: AnalyzePhotoRequest) -> AnalyzePhotoResponse:
    return await analyze_photo(payload, _store(request), _gemini(request))


@app.post('/v1/session/{session_id}/message', response_model=SessionMessageResponse)
async def session_message(request: Request, session_id: str, payload: SessionMessageRequest) -> SessionMessageResponse:
    try:
        return await handle_message(payload.message, _store(request), session_id, _gemini(request))
    except KeyError:
        raise HTTPException(status_code=404, detail='session not found') from None
    except Exception as exc:
        log_error('dialog_failure', session_id=session_id, message=str(exc))
        raise HTTPException(status_code=500, detail='dialog failed') from exc


@app.get('/v1/session/{session_id}', response_model=SessionState)
def get_session(request: Request, session_id: str) -> SessionState:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')
    return session


@app.get('/v1/session/{session_id}/cart', response_model=CartResponse)
def get_cart(request: Request, session_id: str) -> CartResponse:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')
    return _cart_response(session)


@app.post('/v1/session/{session_id}/cart/items', response_model=CartResponse)
def add_cart_item(request: Request, session_id: str, payload: AddCartItemRequest) -> CartResponse:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')

    product = _catalog_item_by_sku(payload.sku)
    if not product:
        raise HTTPException(status_code=404, detail='product not found')

    existing = next((item for item in session.cart.items if item.sku == payload.sku), None)
    if existing:
        existing.quantity += 1
    else:
        session.cart.items.append(
            CartItem(
                sku=product.sku,
                title=product.title,
                brand=product.brand,
                category=product.category,
                domain=product.domain,
                price_value=product.price_value,
                quantity=1,
            )
        )

    _store(request).save(session)
    return _cart_response(session)


@app.patch('/v1/session/{session_id}/cart/items/{sku}', response_model=CartResponse)
def update_cart_item(request: Request, session_id: str, sku: str, payload: UpdateCartItemRequest) -> CartResponse:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')

    item = next((cart_item for cart_item in session.cart.items if cart_item.sku == sku), None)
    if not item:
        raise HTTPException(status_code=404, detail='cart item not found')

    if payload.quantity <= 0:
        session.cart.items = [cart_item for cart_item in session.cart.items if cart_item.sku != sku]
    else:
        item.quantity = payload.quantity

    _store(request).save(session)
    return _cart_response(session)


@app.delete('/v1/session/{session_id}/cart/items/{sku}', response_model=CartResponse)
def remove_cart_item(request: Request, session_id: str, sku: str) -> CartResponse:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')

    session.cart.items = [item for item in session.cart.items if item.sku != sku]
    _store(request).save(session)
    return _cart_response(session)


@app.delete('/v1/session/{session_id}/cart', response_model=CartResponse)
def clear_cart(request: Request, session_id: str) -> CartResponse:
    session = _store(request).get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')

    session.cart.items = []
    _store(request).save(session)
    return _cart_response(session)
