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


def _authorize(client, amount, day, description=None):
    body = {"amount": amount, "occurred_on": day}
    if description is not None:
        body["description"] = description
    return client.post(f"/limits/{CID}/authorize", json=body)


def _statement(client, frm, to, cid=CID):
    return client.get(f"/statements/{cid}", params={"from": frm, "to": to})


def test_statement_lists_only_approved_sorted_with_total(client):
    # Arrange
    client.put(f"/limits/{CID}", json={"daily_limit": "5000.00", "per_transfer_limit": "2000.00"})
    _authorize(client, "1500.00", "2025-03-14", "kira")
    _authorize(client, "2500.00", "2025-03-14", "red")
    _authorize(client, "2000.00", "2025-03-14", "fatura")
    _authorize(client, "1600.00", "2025-03-15", "market")
    _authorize(client, "100.00", "2025-03-13", "erken")

    # Act
    response = _statement(client, "2025-03-13", "2025-03-15")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["customer_id"] == CID
    assert body["from"] == "2025-03-13"
    assert body["to"] == "2025-03-15"
    assert [e["description"] for e in body["entries"]] == ["erken", "kira", "fatura", "market"]
    assert [e["amount"] for e in body["entries"]] == ["100.00", "1500.00", "2000.00", "1600.00"]
    assert body["total"] == "5200.00"


def test_statement_range_is_inclusive_and_excludes_outside(client):
    # Arrange
    for day in ("2025-03-13", "2025-03-14", "2025-03-15", "2025-03-16"):
        _authorize(client, "100.00", day)

    # Act
    body = _statement(client, "2025-03-14", "2025-03-15").json()

    # Assert
    assert [e["occurred_on"] for e in body["entries"]] == ["2025-03-14", "2025-03-15"]
    assert body["total"] == "200.00"


def test_statement_same_day_keeps_approval_order(client):
    # Arrange
    for name in ("a", "b", "c"):
        _authorize(client, "1.00", "2025-03-14", name)

    # Act
    body = _statement(client, "2025-03-14", "2025-03-14").json()

    # Assert
    assert [e["description"] for e in body["entries"]] == ["a", "b", "c"]


def test_statement_entry_without_description_returns_null(client):
    # Arrange
    _authorize(client, "5", "2025-03-14")

    # Act
    entry = _statement(client, "2025-03-14", "2025-03-14").json()["entries"][0]

    # Assert
    assert entry == {"occurred_on": "2025-03-14", "amount": "5.00", "description": None}


def test_statement_total_has_no_float_errors(client):
    # Arrange
    client.put(f"/limits/{CID}", json={"daily_limit": "1.00", "per_transfer_limit": "1.00"})
    for _ in range(3):
        _authorize(client, "0.10", "2025-03-14")

    # Act
    body = _statement(client, "2025-03-14", "2025-03-14").json()

    # Assert
    assert body["total"] == "0.30"


def test_statement_is_empty_for_customer_without_transfers(client):
    # Act
    response = _statement(client, "2025-01-01", "2025-12-31")

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["entries"] == []
    assert body["total"] == "0.00"


def test_statement_accepts_same_from_and_to(client):
    # Act
    response = _statement(client, "2025-03-14", "2025-03-14")

    # Assert
    assert response.status_code == 200


def test_statement_is_isolated_per_customer(client):
    # Arrange
    _authorize(client, "10.00", "2025-03-14")

    # Act
    body = _statement(client, "2025-03-14", "2025-03-14", cid="C000002").json()

    # Assert
    assert body["entries"] == []


def test_statement_rejects_from_after_to(client):
    # Act
    response = _statement(client, "2025-03-15", "2025-03-14")

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"]


def test_statement_rejects_missing_to(client):
    # Act
    response = client.get(f"/statements/{CID}", params={"from": "2025-03-14"})

    # Assert
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_statement_rejects_bad_dates(client):
    # Act
    response = _statement(client, "bugun", "yarin")

    # Assert
    assert response.status_code == 422
    assert "detail" not in response.json()
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
