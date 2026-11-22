"""Transfer business logic."""

import logging
import threading
import uuid
from datetime import datetime, timezone

from . import errors, fees, reports, store
from .models import AccountCreate, TransferRequest

logger = logging.getLogger("aurora.core")

# Single in-process lock: the in-memory store is shared by worker threads, so the
# idempotency check, validation and balance updates must run as one unit.
_lock = threading.Lock()


def create_account(data: AccountCreate) -> dict:
    with _lock:
        if data.id in store.accounts:
            raise errors.account_already_exists(data.id)
        account = data.model_dump()
        store.accounts[data.id] = account
        return account


def execute_transfer(req: TransferRequest, idempotency_key: str | None = None) -> dict:
    with _lock:
        if idempotency_key is not None and idempotency_key in store.idempotency:
            return store.idempotency[idempotency_key]

        # Validate everything first, mutate afterwards (atomic money movement).
        src = store.accounts.get(req.from_account)
        if src is None:
            raise errors.account_not_found(req.from_account)
        dst = store.accounts.get(req.to_account)
        if dst is None:
            raise errors.account_not_found(req.to_account)

        fee = fees.fee_for(req.amount)
        total = req.amount + fee
        if src["balance"] < total:
            raise errors.insufficient_funds(req.from_account)

        src["balance"] = src["balance"] - total
        dst["balance"] = dst["balance"] + req.amount

        transfer = {
            "id": str(uuid.uuid4()),
            "from_account": req.from_account,
            "to_account": req.to_account,
            "amount": req.amount,
            "fee": fee,
            "currency": req.currency,
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        store.transfers[transfer["id"]] = transfer
        if idempotency_key is not None:
            store.idempotency[idempotency_key] = transfer
        reports.record_transfer(transfer, src["owner_name"])

        logger.info(
            "Transfer completed: %s from=%s to=%s",
            transfer["id"],
            req.from_account,
            req.to_account,
        )
        return transfer
