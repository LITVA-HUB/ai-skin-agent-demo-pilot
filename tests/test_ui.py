from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_index_page_served() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'Golden Apple beauty advisor' in response.text
    assert 'beauty-консультант' in response.text or 'beauty advisor' in response.text
    assert 'Сделать дешевле' in response.text
    assert 'Более сияющий' in response.text
    assert 'На вечер' in response.text
    assert 'Натуральнее' in response.text
    assert 'Добавить всё в корзину' in response.text
