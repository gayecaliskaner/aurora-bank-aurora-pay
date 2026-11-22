"""In-memory storage. Limits and usage are kept in separate structures on purpose:
changing limits must never touch past usage."""

import threading
from datetime import date
from decimal import Decimal

# customer_id -> (daily_limit, per_transfer_limit)
limits: dict[str, tuple[Decimal, Decimal]] = {}
# (customer_id, day) -> approved total for that day
usage: dict[tuple[str, date], Decimal] = {}
# customer_id -> approved entries in approval order: (occurred_on, amount, description)
entries: dict[str, list[tuple[date, Decimal, str | None]]] = {}

lock = threading.Lock()


def reset() -> None:
    with lock:
        limits.clear()
        usage.clear()
        entries.clear()
