"""Business rules for limits, authorization and statements.

Inputs are assumed to be already validated by the HTTP layer.
"""

from datetime import date
from decimal import Decimal

from . import store
from .models import (
    AuthorizeInput,
    Decision,
    Limits,
    LimitsInput,
    Statement,
    StatementEntry,
    ValidationFailure,
    format_money,
)

DEFAULT_DAILY_LIMIT = Decimal("10000.00")
DEFAULT_PER_TRANSFER_LIMIT = Decimal("5000.00")

PER_TRANSFER_LIMIT_EXCEEDED = "PER_TRANSFER_LIMIT_EXCEEDED"
DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"


def _limits_response(customer_id: str, daily: Decimal, per: Decimal, source: str) -> Limits:
    return Limits(
        customer_id=customer_id,
        daily_limit=format_money(daily),
        per_transfer_limit=format_money(per),
        source=source,
    )


def set_limits(customer_id: str, data: LimitsInput) -> Limits:
    with store.lock:
        store.limits[customer_id] = (data.daily_limit, data.per_transfer_limit)
    return _limits_response(customer_id, data.daily_limit, data.per_transfer_limit, "custom")


def get_limits(customer_id: str) -> Limits:
    with store.lock:
        custom = store.limits.get(customer_id)
    if custom is None:
        return _limits_response(customer_id, DEFAULT_DAILY_LIMIT, DEFAULT_PER_TRANSFER_LIMIT, "default")
    return _limits_response(customer_id, custom[0], custom[1], "custom")


def authorize(customer_id: str, data: AuthorizeInput) -> Decision:
    # Check and write happen under one lock so concurrent requests cannot overspend.
    with store.lock:
        daily, per = store.limits.get(customer_id, (DEFAULT_DAILY_LIMIT, DEFAULT_PER_TRANSFER_LIMIT))
        key = (customer_id, data.occurred_on)
        used = store.usage.get(key, Decimal("0"))

        reason = None
        if data.amount > per:
            reason = PER_TRANSFER_LIMIT_EXCEEDED
        elif used + data.amount > daily:
            reason = DAILY_LIMIT_EXCEEDED

        if reason is None:
            used += data.amount
            store.usage[key] = used
            store.entries.setdefault(customer_id, []).append((data.occurred_on, data.amount, data.description))

        remaining = daily - used

    return Decision(
        customer_id=customer_id,
        allowed=reason is None,
        reason=reason,
        remaining_daily=format_money(remaining),
    )


def get_statement(customer_id: str, from_: date, to: date) -> Statement:
    if from_ > to:
        raise ValidationFailure("'from' must not be after 'to'")

    with store.lock:
        records = list(store.entries.get(customer_id, []))

    # sorted() is stable: same-day entries keep approval order.
    selected = sorted((r for r in records if from_ <= r[0] <= to), key=lambda r: r[0])
    total = sum((r[1] for r in selected), Decimal("0"))

    return Statement(
        customer_id=customer_id,
        from_=from_.isoformat(),
        to=to.isoformat(),
        entries=[
            StatementEntry(occurred_on=r[0].isoformat(), amount=format_money(r[1]), description=r[2])
            for r in selected
        ],
        total=format_money(total),
    )
