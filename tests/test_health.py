from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_contains_version_and_storage() -> None:
    response = client.get('/health')
    assert response.status_code == 200
    body = response.json()
    assert 'version' in body
    assert body['storage'] in {'in-memory', 'sqlite'}
    assert 'settings_errors' in body
    assert 'gemini_requested_model' in body
    assert 'gemini_last_error' in body
    assert isinstance(body['production_ready'], bool)


def test_ready_endpoint_available() -> None:
    response = client.get('/ready')
    assert response.status_code == 200
    body = response.json()
    assert body['status'] == 'ready'
    assert 'store' in body
    assert 'gemini_last_error' in body
