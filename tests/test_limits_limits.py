import pytest
from fastapi.testclient import TestClient

from services.limits import store
from services.limits.main import app

CID = "C004217"


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()


@pytest.fixture
def client():
    return TestClient(app)


def _assert_envelope(response):
    assert response.status_code == 422
    body = response.json()
    assert "detail" not in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"]


def test_get_limits_returns_defaults_for_unknown_customer(client):
    # Act
    response = client.get(f"/limits/{CID}")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "customer_id": CID,
        "daily_limit": "10000.00",
        "per_transfer_limit": "5000.00",
        "source": "default",
    }


def test_put_limits_then_get_returns_custom_with_two_decimals(client):
    # Act
    put = client.put(f"/limits/{CID}", json={"daily_limit": "5000", "per_transfer_limit": "2000.5"})
    get = client.get(f"/limits/{CID}")

    # Assert
    assert put.status_code == 200
    assert put.json()["source"] == "custom"
    assert get.json()["daily_limit"] == "5000.00"
    assert get.json()["per_transfer_limit"] == "2000.50"
    assert get.json()["source"] == "custom"


def test_put_limits_accepts_per_transfer_equal_to_daily(client):
    # Act
    response = client.put(f"/limits/{CID}", json={"daily_limit": "100.00", "per_transfer_limit": "100.00"})

    # Assert
    assert response.status_code == 200


def test_put_limits_does_not_change_other_customers(client):
    # Arrange
    client.put(f"/limits/{CID}", json={"daily_limit": "100", "per_transfer_limit": "50"})

    # Act
    response = client.get("/limits/C000001")

    # Assert
    assert response.json()["source"] == "default"


@pytest.mark.parametrize(
    "daily,per",
    [
        ("1000.00", "2000.00"),
        ("1000.00", "1000.01"),
        ("0", "0"),
        ("-5", "-5"),
        ("100.123", "50"),
        ("abc", "10"),
        ("", "10"),
        ("NaN", "1"),
        ("Infinity", "1"),
        ("1e3", "1"),
        (" 10", "1"),
    ],
)
def test_put_limits_rejects_invalid_values_with_envelope(client, daily, per):
    # Act
    response = client.put(f"/limits/{CID}", json={"daily_limit": daily, "per_transfer_limit": per})

    # Assert
    _assert_envelope(response)


def test_put_limits_rejects_numeric_json_values(client):
    # Act
    response = client.put(f"/limits/{CID}", json={"daily_limit": 1000, "per_transfer_limit": 10})

    # Assert
    _assert_envelope(response)


def test_put_limits_rejects_missing_field(client):
    # Act
    response = client.put(f"/limits/{CID}", json={"daily_limit": "100.00"})

    # Assert
    _assert_envelope(response)


def test_put_limits_rejects_malformed_json(client):
    # Act
    response = client.put(f"/limits/{CID}", content="{not json", headers={"content-type": "application/json"})

    # Assert
    _assert_envelope(response)


def test_put_limits_keeps_failed_update_out_of_store(client):
    # Arrange
    client.put(f"/limits/{CID}", json={"daily_limit": "500", "per_transfer_limit": "100"})

    # Act
    client.put(f"/limits/{CID}", json={"daily_limit": "10", "per_transfer_limit": "20"})

    # Assert
    assert client.get(f"/limits/{CID}").json()["daily_limit"] == "500.00"
