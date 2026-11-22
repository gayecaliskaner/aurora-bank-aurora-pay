"""API-level tests for Aurora Core reports (handbook sections 2 and 5)."""

import pytest
from fastapi.testclient import TestClient

from services.core import config, store
from services.core.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _reset_store():
    store.reset()


@pytest.fixture
def archive_dir(tmp_path, monkeypatch):
    # Keep every file the archive endpoint writes inside pytest's temp dir.
    target = tmp_path / "archives"
    target.mkdir()
    monkeypatch.setattr(config, "ARCHIVE_DIR", str(target))
    return target


def _account(account_id, owner, balance=1000):
    return client.post(
        "/accounts",
        json={"id": account_id, "owner_name": owner, "iban": f"TR{account_id}", "balance": balance},
    )


def _transfer(from_account, to_account, amount=10):
    return client.post(
        "/transfers", json={"from_account": from_account, "to_account": to_account, "amount": amount}
    )


def _assert_error(resp, status, code):
    assert resp.status_code == status
    assert resp.json()["error"]["code"] == code
    assert "detail" not in resp.json()


# --- GET /reports/transfers ---


def test_report_returns_only_owner_transfers_when_owner_matches():
    _account("A", "Owner A")
    _account("B", "Owner B")
    transfer_id = _transfer("A", "B").json()["id"]
    _transfer("B", "A")

    resp = client.get("/reports/transfers", params={"owner": "Owner A"})

    assert resp.status_code == 200
    assert [row["id"] for row in resp.json()] == [transfer_id]


def test_report_returns_422_when_owner_missing():
    resp = client.get("/reports/transfers")

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_report_returns_empty_list_when_owner_has_no_transfers():
    _account("A", "Owner A")

    resp = client.get("/reports/transfers", params={"owner": "Nobody"})

    assert resp.status_code == 200
    assert resp.json() == []


def test_report_does_not_leak_other_owners_when_owner_contains_sql():
    _account("A", "Owner A")
    _account("B", "Owner B")
    _transfer("A", "B")
    _transfer("B", "A")

    resp = client.get("/reports/transfers", params={"owner": "' OR '1'='1"})

    assert resp.status_code == 200
    assert resp.json() == []


def test_report_finds_transfer_when_owner_name_has_apostrophe():
    _account("A", "O'Brien")
    _account("B", "Owner B")
    transfer_id = _transfer("A", "B").json()["id"]

    resp = client.get("/reports/transfers", params={"owner": "O'Brien"})

    assert resp.status_code == 200
    assert [row["id"] for row in resp.json()] == [transfer_id]


# --- POST /reports/archive ---


def test_archive_creates_file_when_filename_valid(archive_dir):
    resp = client.post("/reports/archive", json={"filename": "stmt-2025"})

    assert resp.status_code == 200
    assert resp.json() == {"exit_code": 0}
    assert (archive_dir / "stmt-2025.tgz").exists()


def test_archive_returns_422_when_filename_missing():
    resp = client.post("/reports/archive", json={})

    _assert_error(resp, 422, "VALIDATION_ERROR")


def test_archive_returns_422_when_filename_empty(archive_dir):
    resp = client.post("/reports/archive", json={"filename": ""})

    _assert_error(resp, 422, "VALIDATION_ERROR")
    assert not (archive_dir / ".tgz").exists()


def test_archive_rejects_filename_when_shell_command_injected(archive_dir, tmp_path):
    marker = tmp_path / "pwned"

    resp = client.post("/reports/archive", json={"filename": f"x; touch {marker} #"})

    _assert_error(resp, 422, "VALIDATION_ERROR")
    assert not marker.exists()


def test_archive_rejects_filename_when_path_traversal(archive_dir, tmp_path):
    resp = client.post("/reports/archive", json={"filename": "../escaped"})

    _assert_error(resp, 422, "VALIDATION_ERROR")
    assert not (tmp_path / "escaped.tgz").exists()
