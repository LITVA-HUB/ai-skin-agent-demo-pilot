from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from .models import (
    AuthAccountResponse,
    AuthForgotPasswordRequest,
    AuthForgotPasswordResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    DemoAccount,
)

UTC = timezone.utc


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _hash_password(password: str, salt: str | None = None) -> str:
    actual_salt = salt or secrets.token_hex(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=actual_salt.encode("utf-8"), n=2**14, r=8, p=1)
    return f"{actual_salt}${derived.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        salt, _ = encoded.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(password, salt), encoded)


def _validate_registration(payload: AuthRegisterRequest) -> tuple[str, str]:
    name = str(payload.name or "").strip()
    email = normalize_email(payload.email)
    if len(name) < 2:
        raise HTTPException(status_code=400, detail='Введите имя')
    if '@' not in email or '.' not in email.split('@')[-1]:
        raise HTTPException(status_code=400, detail='Введите корректный email')
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail='Пароль должен быть не короче 6 символов')
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail='Пароли не совпадают')
    return name, email


def _account_response(account: DemoAccount) -> AuthAccountResponse:
    return AuthAccountResponse(account_id=account.account_id, name=account.name, email=account.email)


def register_account(store, payload: AuthRegisterRequest) -> AuthAccountResponse:
    name, email = _validate_registration(payload)
    if store.get_account_by_email(email):
        raise HTTPException(status_code=400, detail='Аккаунт с этим email уже существует')
    now_iso = _now_iso()
    account = DemoAccount(
        account_id=str(uuid.uuid4()),
        name=name,
        email=email,
        password_hash=_hash_password(payload.password),
        created_at=now_iso,
        updated_at=now_iso,
    )
    saved = store.create_account(account)
    return _account_response(saved)


def login_account(store, payload: AuthLoginRequest) -> AuthAccountResponse:
    email = normalize_email(payload.email)
    account = store.get_account_by_email(email)
    if not account or not _verify_password(payload.password, account.password_hash):
        raise HTTPException(status_code=401, detail='Неверный email или пароль')
    return _account_response(account)


def forgot_password(store, payload: AuthForgotPasswordRequest) -> AuthForgotPasswordResponse:
    email = normalize_email(payload.email)
    _ = store.get_account_by_email(email)
    return AuthForgotPasswordResponse(message='Если аккаунт существует, мы уже отправили ссылку для входа.')


def load_account(store, account_id: str) -> AuthAccountResponse:
    account = store.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail='account not found')
    return _account_response(account)
