from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_page_served() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'Golden Apple' in response.text
    assert 'Beauty ID' in response.text
    assert 'Beauty Access' in response.text
    assert 'Beauty ID Scan' in response.text
    assert 'Скан лица и быстрый переход к beauty advisor.' in response.text
    assert 'Продолжить в Beauty ID' in response.text
    assert 'Создать аккаунт' in response.text
    assert 'Войти' in response.text
    assert 'Начните со скана' in response.text
    assert 'Поднесите лицо к камере' in response.text
    assert 'С камеры' in response.text
    assert 'Загрузить фото' in response.text
    assert 'Beauty advisor' in response.text
    assert 'Что советует advisor' in response.text
    assert 'С чего я бы начал' in response.text
    assert 'AI · проверка…' in response.text
    assert 'Корзина' in response.text
    assert 'Сделать дешевле' in response.text
    assert 'Более сияющий' in response.text
    assert 'На вечер' in response.text
    assert 'Натуральнее' in response.text
    assert 'Добавить весь набор' in response.text


def test_index_page_contains_beauty_id_cabinet_and_halal_copy() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'Beauty ID' in response.text
    assert 'Личный кабинет' in response.text
    assert 'История анализов' in response.text
    assert 'Халяль' in response.text
    assert 'Оформить демо-заказ' in response.text


def test_advisor_and_profile_routes_render_shell() -> None:
    advisor = client.get('/advisor')
    profile = client.get('/profile')

    assert advisor.status_code == 200
    assert 'Beauty ID готов' in advisor.text
    assert 'Чат с advisor' in advisor.text
    assert 'Что мы учитываем сейчас' in advisor.text
    assert 'Ваш результат' in advisor.text
    assert 'С чего я бы начал' in advisor.text
    assert 'Добавить весь набор' in advisor.text

    assert profile.status_code == 200
    assert 'Личный кабинет' in profile.text
    assert 'Что система запомнила о вас' in profile.text
    assert 'Что учитывать в подборе' in profile.text
    assert 'История заказов' in profile.text


def test_scan_led_future_visual_hooks_are_absent() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'data-visual-mode="scan-led-future"' not in response.text
    assert 'scan-aura' not in response.text
    assert 'scan-orbit' not in response.text
    assert 'message-fresh' not in response.text
    assert 'transition-orbit' not in response.text


def test_cart_template_contains_remove_controls() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'window.decrementCartItem' in response.text
    assert 'window.removeCartItem' in response.text
    assert 'Удалить' in response.text


def test_access_profile_helpers_are_present() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'beauty-id-account-id' in response.text
    assert 'beauty-id-access-profile' not in response.text
    assert 'loadCurrentAccount' in response.text
    assert 'registerForm' in response.text
    assert 'loginForm' in response.text
    assert 'forgotPasswordForm' in response.text
    assert 'Создать аккаунт' in response.text
    assert 'Войти' in response.text
    assert 'Забыли пароль?' in response.text
    assert 'Выйти' in response.text
