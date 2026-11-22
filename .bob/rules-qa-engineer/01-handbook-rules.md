# Aurora Pay rules for the QA Engineer mode

Source: `docs/ENGINEERING-HANDBOOK.md` (v3.1, sections 1, 2, 3 and 5). If this file and the
handbook ever differ, the handbook wins. Assert against these rules in tests; never weaken a
test to match behavior that breaks them.

## 1. Money (handbook section 1)

- Amounts are `decimal.Decimal` in code. No `float` arithmetic on money.
- Rounding is `ROUND_HALF_UP`, 2 decimal places.
- The API converts incoming amounts to `Decimal`. Response amounts may be a JSON number or a
  string, but must be exact to the cent (`99.00`, never `99.00000000000006`).
- Fee rules: `docs/FEE-POLICY.md` is the only source.

## 2. Error handling (handbook section 2)

Every error uses one envelope. A bare `{"detail": ...}` body, a stack trace or an internal
error message must never reach the client.

```json
{"error": {"code": "ACCOUNT_NOT_FOUND", "message": "Hesap bulunamadı: ACC-9999"}}
```

| Situation | HTTP | `code` |
|---|---|---|
| Invalid input (missing field, amount <= 0, negative balance, type error) | 422 | `VALIDATION_ERROR` |
| Sender and receiver are the same account | 422 | `VALIDATION_ERROR` |
| Account not found | 404 | `ACCOUNT_NOT_FOUND` |
| Account already exists (second record with the same `id`) | 409 | `ACCOUNT_ALREADY_EXISTS` |
| Transfer not found | 404 | `TRANSFER_NOT_FOUND` |
| Insufficient funds | 409 | `INSUFFICIENT_FUNDS` |
| Unexpected error | 500 | `INTERNAL_ERROR` (fixed message: "Beklenmeyen bir hata oluştu") |

Additional rules:

- Money movement is atomic: if any step fails, no balance has changed. Validate first, then write.
- Money-moving endpoints support the `Idempotency-Key` header. A second request with the same key
  creates no new operation and returns the first response.
- Unexpected errors are logged server-side in detail; the client only sees `INTERNAL_ERROR`.

## 3. Logging (handbook section 3)

- No PII in logs: full name, IBAN, national ID (TCKN), phone, e-mail, card number.
- Log lines use technical ids only: `account_id`, `transfer_id`.
- Logging goes through the `logging` module. `print` is not used.

## 4. Security (handbook section 5)

- No secrets (API key, password, JWT secret) in code or repo; read them from environment variables.
- SQL is always parameterized; user input is never concatenated into SQL.
- No shell command is run with user input. File names are validated and path traversal (`..`) is rejected.
- Docker images run as a non-root user, do not use `ADD <url>`, and contain no embedded secrets.
- Infrastructure code has no open-to-the-world (`0.0.0.0/0`) rules, no public buckets and no
  unencrypted storage.
- Dependencies are not kept at known-vulnerable versions.

## How to use these rules as a tester

- Turn each applicable rule into an API-level assertion (status code, `error.code`, exact amount,
  unchanged balances after a failed transfer, replayed `Idempotency-Key`).
- Never put real-looking PII or secrets in test data.
- A test that fails because the source breaks one of these rules is a valid result. Report it with
  the handbook section number.
