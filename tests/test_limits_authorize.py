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


def _set_limits(client, daily, per, cid=CID):
    assert client.put(f"/limits/{cid}", json={"daily_limit": daily, "per_transfer_limit": per}).status_code == 200


def _authorize(client, amount, day="2025-03-14", description=None, cid=CID):
    body = {"amount": amount, "occurred_on": day}
    if description is not None:
        body["description"] = description
    return client.post(f"/limits/{cid}/authorize", json=body)


def test_authorize_prd_example_scenario_matches_table(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")
    steps = [
        ("1500.00", "2025-03-14", True, None, "3500.00"),
        ("2500.00", "2025-03-14", False, "PER_TRANSFER_LIMIT_EXCEEDED", "3500.00"),
        ("2000.00", "2025-03-14", True, None, "1500.00"),
        ("1600.00", "2025-03-14", False, "DAILY_LIMIT_EXCEEDED", "1500.00"),
        ("1600.00", "2025-03-15", True, None, "3400.00"),
    ]

    for amount, day, allowed, reason, remaining in steps:
        # Act
        response = _authorize(client, amount, day)

        # Assert
        assert response.status_code == 200
        assert response.json() == {
            "customer_id": CID,
            "allowed": allowed,
            "reason": reason,
            "remaining_daily": remaining,
        }


def test_authorize_amount_equal_to_per_transfer_limit_is_allowed(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")

    # Act
    body = _authorize(client, "2000.00").json()

    # Assert
    assert body["allowed"] is True


def test_authorize_amount_just_over_per_transfer_limit_is_rejected(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")

    # Act
    body = _authorize(client, "2000.01").json()

    # Assert
    assert body["allowed"] is False
    assert body["reason"] == "PER_TRANSFER_LIMIT_EXCEEDED"


def test_authorize_reaching_daily_limit_exactly_is_allowed_then_penny_rejected(client):
    # Arrange
    _set_limits(client, "2000.00", "2000.00")

    # Act
    first = _authorize(client, "2000.00").json()
    second = _authorize(client, "0.01").json()

    # Assert
    assert first["allowed"] is True
    assert first["remaining_daily"] == "0.00"
    assert second["allowed"] is False
    assert second["reason"] == "DAILY_LIMIT_EXCEEDED"
    assert second["remaining_daily"] == "0.00"


def test_authorize_per_transfer_reason_has_priority_when_both_exceeded(client):
    # Arrange
    _set_limits(client, "3000.00", "1000.00")
    _authorize(client, "1000.00")
    _authorize(client, "1000.00")

    # Act
    body = _authorize(client, "2500.00").json()

    # Assert
    assert body["reason"] == "PER_TRANSFER_LIMIT_EXCEEDED"


def test_authorize_uses_default_limits_when_not_configured(client):
    # Act
    ok = _authorize(client, "5000.00").json()
    rejected = _authorize(client, "5000.01").json()

    # Assert
    assert ok["allowed"] is True
    assert ok["remaining_daily"] == "5000.00"
    assert rejected["reason"] == "PER_TRANSFER_LIMIT_EXCEEDED"


def test_authorize_rejected_transfer_does_not_consume_usage(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")
    _authorize(client, "1500.00")
    _authorize(client, "2500.00")

    # Act
    body = _authorize(client, "2000.00").json()

    # Assert
    assert body["allowed"] is True
    assert body["remaining_daily"] == "1500.00"


def test_authorize_usage_is_independent_across_days(client):
    # Arrange
    _set_limits(client, "4000.00", "2000.00")
    _authorize(client, "2000.00", day="2025-03-14")
    _authorize(client, "2000.00", day="2025-03-14")

    # Act
    body = _authorize(client, "2000.00", day="2025-03-15").json()

    # Assert
    assert body["allowed"] is True
    assert body["remaining_daily"] == "2000.00"


def test_authorize_usage_is_independent_across_customers(client):
    # Arrange
    _set_limits(client, "2000.00", "2000.00")
    _authorize(client, "2000.00")

    # Act
    body = _authorize(client, "2000.00", cid="C000002").json()

    # Assert
    assert body["allowed"] is True


def test_authorize_limit_change_keeps_existing_usage(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")
    _authorize(client, "2000.00")
    _set_limits(client, "6000.00", "3000.00")

    # Act
    body = _authorize(client, "1000.00").json()

    # Assert
    assert body["allowed"] is True
    assert body["remaining_daily"] == "3000.00"


def test_authorize_lowering_limit_below_usage_rejects_further_transfers(client):
    # Arrange
    _set_limits(client, "5000.00", "2000.00")
    _authorize(client, "2000.00")
    _set_limits(client, "1000.00", "1000.00")

    # Act
    body = _authorize(client, "100.00").json()

    # Assert
    assert body["allowed"] is False
    assert body["reason"] == "DAILY_LIMIT_EXCEEDED"
    assert body["remaining_daily"] == "-1000.00"


def test_authorize_has_no_float_rounding_errors(client):
    # Arrange
    _set_limits(client, "0.30", "0.30")

    # Act
    results = [_authorize(client, "0.10").json() for _ in range(4)]

    # Assert
    assert [r["allowed"] for r in results] == [True, True, True, False]
    assert results[2]["remaining_daily"] == "0.00"


def test_authorize_accepts_amount_without_or_with_one_decimal(client):
    # Arrange
    _set_limits(client, "100.00", "100.00")

    # Act
    first = _authorize(client, "10").json()
    second = _authorize(client, "10.5").json()

    # Assert
    assert first["remaining_daily"] == "90.00"
    assert second["remaining_daily"] == "79.50"


def test_authorize_accepts_null_description(client):
    # Act
    response = client.post(
        f"/limits/{CID}/authorize",
        json={"amount": "10.00", "occurred_on": "2025-03-14", "description": None},
    )

    # Assert
    assert response.status_code == 200


@pytest.mark.parametrize("amount", ["0", "0.00", "-1.00", "abc", "10.999", "", "NaN", "1e2"])
def test_authorize_rejects_invalid_amount_with_envelope(client, amount):
    # Act
    response = _authorize(client, amount)

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("day", ["2025-13-45", "2025-02-30", "14-03-2025", "bugun", "2025-03-14T00:00:00", ""])
def test_authorize_rejects_invalid_date_with_envelope(client, day):
    # Act
    response = _authorize(client, "10.00", day=day)

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "detail" not in response.json()


def test_authorize_rejects_missing_fields_with_envelope(client):
    # Act
    response = client.post(f"/limits/{CID}/authorize", json={"amount": "10.00"})

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_authorize_invalid_request_does_not_record_anything(client):
    # Arrange
    _authorize(client, "abc")

    # Act
    body = client.get(f"/statements/{CID}", params={"from": "2025-01-01", "to": "2025-12-31"}).json()

    # Assert
    assert body["entries"] == []
