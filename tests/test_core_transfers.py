"""API-level tests for Aurora Core transfers (INCIDENT-2041)."""

import threading
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from services.core import store
from services.core.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()


def _dec(value) -> Decimal:
    return Decimal(str(value))


def _account(account_id, balance):
    return client.post(
        "/accounts",
        json={"id": account_id, "owner_name": f"Owner {account_id}", "iban": f"TR{account_id}", "balance": balance},
    )


def _balance(account_id) -> Decimal:
    return _dec(client.get(f"/accounts/{account_id}").json()["balance"])


def _transfer(amount, to="B", headers=None):
    return client.post("/transfers", json={"from_account": "A", "to_account": to, "amount": amount}, headers=headers)


def _assert_error(resp, status, code):
    assert resp.status_code == status
    assert resp.json()["error"]["code"] == code
    assert "detail" not in resp.json()


def test_transfer_moves_money_and_charges_fee_when_funds_sufficient():
    _account("A", 1000)
    _account("B", 0)

    resp = _transfer(100)

    assert resp.status_code == 201
    assert _dec(resp.json()["fee"]) == Decimal("0.50")
    assert _balance("A") == Decimal("899.50")
    assert _balance("B") == Decimal("100")


def test_transfer_replays_first_response_when_idempotency_key_repeated():
    _account("A", 1000)
    _account("B", 0)
    headers = {"Idempotency-Key": "k-1"}

    first = _transfer(100, headers=headers)
    second = _transfer(100, headers=headers)

    assert first.json()["id"] == second.json()["id"]
    assert _balance("B") == Decimal("100")


def test_transfer_debits_once_when_same_idempotency_key_sent_concurrently():
    _account("A", 10000)
    _account("B", 0)
    results = []

    def send():
        results.append(_transfer(100, headers={"Idempotency-Key": "k-race"}).json()["id"])

    threads = [threading.Thread(target=send) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(results)) == 1
    assert _balance("B") == Decimal("100")


def test_transfer_returns_404_and_keeps_balance_when_recipient_unknown():
    _account("A", 1000)

    resp = _transfer(100, to="ACC-9999")

    _assert_error(resp, 404, "ACCOUNT_NOT_FOUND")
    assert _balance("A") == Decimal("1000")


def test_transfer_returns_404_when_sender_unknown():
    _account("B", 0)

    resp = client.post("/transfers", json={"from_account": "NOPE", "to_account": "B", "amount": 1})

    _assert_error(resp, 404, "ACCOUNT_NOT_FOUND")


def test_transfer_keeps_cent_precision_when_amounts_have_decimals():
    _account("A", 100.10)
    _account("B", 0)

    _transfer(10.10)

    assert _balance("A") == Decimal("89.95")
    assert _balance("B") == Decimal("10.10")


@pytest.mark.parametrize(
    "amount, fee",
    [
        (0.01, "0.00"),
        (3, "0.02"),
        (10.10, "0.05"),
        (999.99, "5.00"),
        (1000, "2.50"),
        (1234.56, "3.09"),
    ],
)
def test_transfer_fee_matches_policy_when_amount_at_boundaries(amount, fee):
    _account("A", 100000)
    _account("B", 0)

    resp = _transfer(amount)

    assert _dec(resp.json()["fee"]) == Decimal(fee)


def test_transfer_returns_409_when_funds_insufficient():
    _account("A", 50)
    _account("B", 0)

    resp = _transfer(500)

    _assert_error(resp, 409, "INSUFFICIENT_FUNDS")
    assert _balance("A") == Decimal("50")


def test_transfer_succeeds_when_balance_equals_amount_plus_fee():
    _account("A", 100.50)
    _account("B", 0)

    resp = _transfer(100)

    assert resp.status_code == 201
    assert _balance("A") == Decimal("0")


@pytest.mark.parametrize("amount", [-5, 0, "abc", 1.005])
def test_transfer_returns_422_when_amount_invalid(amount):
    _account("A", 1000)
    _account("B", 0)

    resp = _transfer(amount)

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_transfer_returns_422_when_field_missing():
    resp = client.post("/transfers", json={"from_account": "A"})

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_transfer_returns_422_when_sender_equals_recipient():
    _account("A", 1000)

    resp = _transfer(10, to="A")

    _assert_error(resp, 422, "VALIDATION_ERROR")
    assert _balance("A") == Decimal("1000")


def test_transfer_returns_422_when_body_is_not_json():
    resp = client.post("/transfers", content="not-json", headers={"Content-Type": "application/json"})

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_account_create_returns_409_when_id_already_exists():
    _account("A", 10)

    resp = _account("A", 20)

    _assert_error(resp, 409, "ACCOUNT_ALREADY_EXISTS")
    assert _balance("A") == Decimal("10")


def test_account_create_returns_422_when_balance_negative():
    resp = _account("A", -1)

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_account_get_returns_404_when_unknown():
    _assert_error(client.get("/accounts/NOPE"), 404, "ACCOUNT_NOT_FOUND")


def test_transfer_get_returns_404_when_unknown():
    _assert_error(client.get("/transfers/NOPE"), 404, "TRANSFER_NOT_FOUND")


def test_transfer_get_returns_transfer_when_exists():
    _account("A", 1000)
    _account("B", 0)
    transfer_id = _transfer(100).json()["id"]

    resp = client.get(f"/transfers/{transfer_id}")

    assert resp.status_code == 200
    assert resp.json()["id"] == transfer_id


def test_unknown_route_returns_error_envelope():
    resp = client.get("/no-such-route")

    assert resp.status_code == 404
    assert "error" in resp.json()


def test_unexpected_error_returns_500_internal_error_without_details(monkeypatch):
    _account("A", 1000)
    _account("B", 0)

    def boom(*_args, **_kwargs):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("services.core.service.reports.record_transfer", boom)

    resp = _transfer(100)

    _assert_error(resp, 500, "INTERNAL_ERROR")
    assert resp.json()["error"]["message"] == "Beklenmeyen bir hata oluştu"
    assert "secret" not in resp.text
