import pytest
from fastapi.testclient import TestClient

from services.limits import service, store
from services.limits.main import app


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.parametrize("bad_id", ["X123456", "C12345", "C1234567", "c123456", "C12345A"])
def test_invalid_customer_id_returns_validation_envelope(client, bad_id):
    # Act
    response = client.get(f"/limits/{bad_id}")

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "detail" not in response.json()


@pytest.mark.parametrize(
    "method,path",
    [
        ("put", "/limits/X1"),
        ("post", "/limits/X1/authorize"),
        ("get", "/statements/X1?from=2025-01-01&to=2025-01-02"),
    ],
)
def test_invalid_customer_id_is_rejected_on_every_endpoint(client, method, path):
    # Act
    response = client.request(method, path, json={})

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_valid_customer_id_boundaries_are_accepted(client):
    # Act
    response = client.get("/limits/C000000")

    # Assert
    assert response.status_code == 200


def test_unknown_route_returns_error_envelope(client):
    # Act
    response = client.get("/nope")

    # Assert
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_wrong_method_returns_error_envelope(client):
    # Act
    response = client.delete("/limits/C000001")

    # Assert
    assert response.status_code == 405
    assert response.json()["error"]["code"] == "METHOD_NOT_ALLOWED"


def test_unexpected_error_returns_internal_error_without_details(monkeypatch):
    # Arrange
    def boom(customer_id):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(service, "get_limits", boom)
    client = TestClient(app, raise_server_exceptions=False)

    # Act
    response = client.get("/limits/C000001")

    # Assert
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Beklenmeyen bir hata oluştu"}}
    assert "secret" not in response.text
