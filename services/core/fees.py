"""Transfer fee calculation. See docs/FEE-POLICY.md."""

from decimal import ROUND_HALF_UP, Decimal

THRESHOLD = Decimal("1000.00")
LOW_RATE = Decimal("0.005")
HIGH_RATE = Decimal("0.0025")
CENT = Decimal("0.01")


def fee_for(amount: Decimal) -> Decimal:
    rate = HIGH_RATE if amount >= THRESHOLD else LOW_RATE
    return (amount * rate).quantize(CENT, rounding=ROUND_HALF_UP)
