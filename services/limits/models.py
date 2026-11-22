"""Request/response models and money/date parsing for the limits service."""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

_MONEY_RE = re.compile(r"[0-9]+(\.[0-9]{1,2})?")
_DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_CENT = Decimal("0.01")


class ValidationFailure(Exception):
    """Business-level input validation error, rendered as a 422 error envelope."""


def parse_money(value: Any) -> Decimal:
    """Parse a positive amount string with at most 2 decimals into a Decimal."""
    if not isinstance(value, str) or not _MONEY_RE.fullmatch(value):
        raise ValueError("amount must be a string with at most 2 decimals, e.g. '1000' or '1000.50'")
    amount = Decimal(value)
    if amount <= 0:
        raise ValueError("amount must be greater than 0")
    return amount


def format_money(value: Decimal) -> str:
    return str(value.quantize(_CENT, rounding=ROUND_HALF_UP))


def parse_date(value: Any) -> date:
    if not isinstance(value, str) or not _DATE_RE.fullmatch(value):
        raise ValueError("date must be in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("date is not a valid calendar date") from None


Money = Annotated[Decimal, BeforeValidator(parse_money)]
IsoDate = Annotated[date, BeforeValidator(parse_date)]


class LimitsInput(BaseModel):
    daily_limit: Money
    per_transfer_limit: Money

    @model_validator(mode="after")
    def _per_transfer_within_daily(self) -> "LimitsInput":
        if self.per_transfer_limit > self.daily_limit:
            raise ValueError("per_transfer_limit must not exceed daily_limit")
        return self


class Limits(BaseModel):
    customer_id: str
    daily_limit: str
    per_transfer_limit: str
    source: str


class AuthorizeInput(BaseModel):
    amount: Money
    occurred_on: IsoDate
    description: str | None = None


class Decision(BaseModel):
    customer_id: str
    allowed: bool
    reason: str | None
    remaining_daily: str


class StatementEntry(BaseModel):
    occurred_on: str
    amount: str
    description: str | None


class Statement(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer_id: str
    from_: str = Field(alias="from")
    to: str
    entries: list[StatementEntry]
    total: str
