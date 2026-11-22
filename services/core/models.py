from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

# Money is always Decimal with at most 2 decimal places (ENGINEERING-HANDBOOK section 1).
PositiveMoney = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)]


class AccountCreate(BaseModel):
    id: str
    owner_name: str
    iban: str
    balance: NonNegativeMoney
    currency: str = "TRY"


class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: PositiveMoney
    currency: str = "TRY"
    note: str | None = None

    @model_validator(mode="after")
    def _accounts_differ(self):
        if self.from_account == self.to_account:
            raise ValueError("Gönderen ve alıcı hesap aynı olamaz")
        return self


class ArchiveRequest(BaseModel):
    # Letters, digits, "_" and "-" only: no path separators, dots or shell metacharacters.
    filename: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
