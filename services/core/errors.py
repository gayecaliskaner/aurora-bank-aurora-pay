"""Application errors mapped to the handbook error envelope (ENGINEERING-HANDBOOK section 2)."""


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def account_not_found(account_id: str) -> AppError:
    return AppError(404, "ACCOUNT_NOT_FOUND", f"Hesap bulunamadı: {account_id}")


def account_already_exists(account_id: str) -> AppError:
    return AppError(409, "ACCOUNT_ALREADY_EXISTS", f"Hesap zaten var: {account_id}")


def transfer_not_found(transfer_id: str) -> AppError:
    return AppError(404, "TRANSFER_NOT_FOUND", f"Transfer bulunamadı: {transfer_id}")


def insufficient_funds(account_id: str) -> AppError:
    return AppError(409, "INSUFFICIENT_FUNDS", f"Yetersiz bakiye: {account_id}")
