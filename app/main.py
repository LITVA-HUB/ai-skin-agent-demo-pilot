from __future__ import annotations

from pathlib import Path
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from .beauty_id import allergen_library, build_cabinet, build_profile_summary
from .catalog import load_catalog
from .logic import analyze_photo, handle_message
from .auth_service import forgot_password, load_account, login_account, register_account
from .models import (
    AddCartItemRequest,
    AnalyzePhotoRequest,
    AuthForgotPasswordRequest,
    AuthForgotPasswordResponse,
    AuthAccountResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    CartItem,
    CartResponse,
    CheckoutResponse,
    DemoOrderItem,
    OrderHistoryEntry,
    SessionMessageRequest,
    SessionMessageResponse,
    SessionState,
    UpdateCartItemRequest,
)
from .observability import log_error
from .runtime import lifespan, build_runtime
from .config import validate_settings

APP_VERSION = '0.6.0'
app = FastAPI(title='Golden Apple Beauty ID / AI Beauty Advisor', version=APP_VERSION, lifespan=lifespan)
TEMPLATE_DIR = Path(__file__).parent / 'templates'
UTC = timezone.utc


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


def _cabinet_payload(store, session: SessionState):
    profile = build_profile_summary(session)
    store.save_profile(profile)
    return build_cabinet(profile, store.list_analysis_history(session.demo_user_id), store.list_order_history(session.demo_user_id))


def _product_svg(product) -> str:
    badge = product.hero_badge or 'Выбор Beauty ID'
    price = f"{product.price_value} ₽"
    subtitle = product.category.value.replace('_', ' ').title()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="720" viewBox="0 0 720 720">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#f8f1e8"/>
        <stop offset="100%" stop-color="#f2dfc6"/>
      </linearGradient>
    </defs>
    <rect width="720" height="720" rx="36" fill="url(#bg)"/>
    <circle cx="565" cy="155" r="118" fill="#d3a24a" opacity="0.14"/>
    <circle cx="175" cy="560" r="140" fill="#6f355e" opacity="0.10"/>
    <rect x="102" y="108" width="516" height="504" rx="36" fill="#fffaf4" stroke="#d7c7b2"/>
    <rect x="152" y="160" width="416" height="230" rx="28" fill="#f0e4d2"/>
    <text x="360" y="240" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" fill="#8c775d">Golden Apple demo</text>
    <text x="360" y="295" text-anchor="middle" font-family="Arial, sans-serif" font-size="46" font-weight="700" fill="#1f1a16">{product.brand}</text>
    <text x="360" y="340" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" fill="#4a4038">{subtitle}</text>
    <rect x="152" y="422" width="240" height="42" rx="21" fill="#171411" opacity="0.08"/>
    <text x="272" y="449" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" fill="#493d33">{badge}</text>
    <text x="152" y="515" font-family="Arial, sans-serif" font-size="34" font-weight="700" fill="#171411">{product.title[:34]}</text>
    <text x="152" y="558" font-family="Arial, sans-serif" font-size="28" fill="#6a5d52">{price}</text>
    <text x="152" y="602" font-family="Arial, sans-serif" font-size="22" fill="#8a7d70">Визуал карточки товара</text>
    </svg>'''


@app.post('/v1/auth/register', response_model=AuthAccountResponse)
def auth_register(request: Request, payload: AuthRegisterRequest) -> AuthAccountResponse:
    return register_account(_store(request), payload)


@app.post('/v1/auth/login', response_model=AuthAccountResponse)
def auth_login(request: Request, payload: AuthLoginRequest) -> AuthAccountResponse:
    return login_account(_store(request), payload)


@app.post('/v1/auth/forgot-password', response_model=AuthForgotPasswordResponse)
def auth_forgot_password(request: Request, payload: AuthForgotPasswordRequest) -> AuthForgotPasswordResponse:
    return forgot_password(_store(request), payload)


@app.get('/v1/auth/me', response_model=AuthAccountResponse)
def auth_me(request: Request, account_id: str) -> AuthAccountResponse:
    return load_account(_store(request), account_id)


@app.get('/', response_class=HTMLResponse)
@app.get('/advisor', response_class=HTMLResponse)
@app.get('/profile', response_class=HTMLResponse)
def index() -> HTMLResponse:
    return HTMLResponse((TEMPLATE_DIR / 'index.html').read_text(encoding='utf-8'))


@app.get('/health')
def health(request: Request) -> dict[str, object]:
    store = _store(request)
    gemini = _gemini(request)
    settings_errors = _settings_errors(request)
    store_stats = store.stats()
    active_provider = getattr(gemini, 'active_provider', getattr(gemini, 'provider', 'gemini'))
    requested_provider = getattr(gemini, 'provider', active_provider)
    configured = bool(gemini.api_key)
    active_model = getattr(gemini, 'active_model', gemini.model)
    last_error = getattr(gemini, 'last_error', None)
    return {
        'status': 'ok',
        'version': request.app.version,
        'storage': store_stats.get('backend', 'in-memory'),
        'ai_provider': active_provider,
        'ai_requested_provider': requested_provider,
        'ai_configured': configured,
        'ai_model': active_model,
        'ai_requested_model': gemini.model,
        'ai_last_error': last_error,
        'gemini_configured': configured,
        'gemini_model': active_model,
        'gemini_requested_model': gemini.model,
        'gemini_last_error': last_error,
        'settings_errors': settings_errors,
        'production_ready': configured and not last_error and not settings_errors and store_stats.get('backend') == 'sqlite',
    }


@app.get('/ready')
def ready(request: Request) -> dict[str, object]:
    store = _store(request)
    gemini = _gemini(request)
    active_provider = getattr(gemini, 'active_provider', getattr(gemini, 'provider', 'gemini'))
    active_model = getattr(gemini, 'active_model', gemini.model)
    last_error = getattr(gemini, 'last_error', None)
    return {
        'status': 'ready',
        'version': request.app.version,
        'store': store.stats(),
        'ai_provider': active_provider,
        'ai_configured': bool(gemini.api_key),
        'ai_model': active_model,
        'ai_last_error': last_error,
        'gemini_configured': bool(gemini.api_key),
        'gemini_model': active_model,
        'gemini_last_error': last_error,
        'settings_errors': _settings_errors(request),
    }


@app.get('/v1/preferences/allergens')
def get_allergen_library():
    return allergen_library()


@app.get('/v1/product-media/{sku}')
def product_media(sku: str):
    product = _catalog_item_by_sku(sku)
    if not product:
        raise HTTPException(status_code=404, detail='product not found')
    return Response(content=_product_svg(product), media_type='image/svg+xml')


@app.post('/v1/photo/analyze')
async def analyze_photo_endpoint(request: Request, payload: AnalyzePhotoRequest):
    return await analyze_photo(payload, _store(request), _gemini(request))


@app.post('/v1/session/{session_id}/message')
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


@app.get('/v1/profile/demo')
def get_demo_profile(request: Request, account_id: str = 'demo-user'):
    store = _store(request)
    profile = store.get_profile(account_id)
    if profile is None:
        placeholder = SessionState.model_validate({
            'session_id': 'demo-profile',
            'photo_analysis': {},
            'skin_profile': {'skin_type': 'normal', 'primary_concerns': [], 'confidence_overall': 0.0},
            'current_plan': {'required_categories': []},
            'user_preferences': {},
            'demo_user_id': account_id,
        })
        profile = build_profile_summary(placeholder)
        account = store.get_account(account_id)
        if account:
            profile.name = account.name
        store.save_profile(profile)
    return build_cabinet(profile, store.list_analysis_history(account_id), store.list_order_history(account_id))


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
                image_url=product.image_url,
                goldapple_url=product.goldapple_url,
                goldapple_search_query=product.goldapple_search_query,
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


@app.post('/v1/session/{session_id}/checkout', response_model=CheckoutResponse)
def checkout(request: Request, session_id: str) -> CheckoutResponse:
    store = _store(request)
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail='session not found')
    if not session.cart.items:
        raise HTTPException(status_code=400, detail='cart is empty')

    order = OrderHistoryEntry(
        order_id=str(uuid.uuid4()),
        session_id=session_id,
        created_at=datetime.now(UTC).isoformat(),
        total_items=session.cart.total_items,
        total_price=session.cart.total_price,
        status='demo_saved',
        items=[
            DemoOrderItem(
                sku=item.sku,
                title=item.title,
                brand=item.brand,
                quantity=item.quantity,
                price_value=item.price_value,
                image_url=item.image_url,
            )
            for item in session.cart.items
        ],
    )
    store.add_order_history(session.demo_user_id, order)
    session.cart.items = []
    store.save(session)
    return CheckoutResponse(order=order, cart_cleared=True, message='Demo checkout saved to order history. Live e-commerce handoff can be connected next.')
