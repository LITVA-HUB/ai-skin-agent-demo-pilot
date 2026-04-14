from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_page_served() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'Golden Apple' in response.text
    assert 'Beauty ID' in response.text
    assert 'Beauty ID Scan' in response.text
    assert 'Скан лица и быстрый переход к beauty advisor.' in response.text
    assert 'Начните со скана' in response.text
    assert 'Поднесите лицо к камере' in response.text
    assert 'С камеры' in response.text
    assert 'Загрузить фото' in response.text
    assert 'Beauty advisor' in response.text
    assert 'Что советует advisor' in response.text
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
    assert 'Добавить весь набор' in advisor.text

    assert profile.status_code == 200
    assert 'Личный кабинет' in profile.text
    assert 'Что система запомнила о вас' in profile.text
    assert 'Что учитывать в подборе' in profile.text
    assert 'История заказов' in profile.text
