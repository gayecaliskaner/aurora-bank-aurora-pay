---
name: write-api-tests
description: Use when the user asks to write, add, extend or run tests for an aurora-pay feature or endpoint, or to raise services/core coverage to the 85% threshold. Walks through the handbook test standard step by step.
---

# Write API-level tests (Aurora Pay)

Procedure for writing tests that follow `docs/ENGINEERING-HANDBOOK.md` section 4. Only create or
edit files under `tests/`. Never change source, docs or CI to make a test pass.

1. **Read the standard.** Use `read_file` on `docs/ENGINEERING-HANDBOOK.md`. Also read
   `docs/FEE-POLICY.md` if the feature involves fees, and `docs/API-SPEC-limits.yaml` or
   `docs/PRD-limits.md` if it involves the limits service.

2. **Understand the feature.** Use `read_file`, `grep` or `FindSymbol` on the endpoint and its
   service code under `services/`. List the endpoints, request fields, success response and
   every error the feature can return.

3. **Match existing style.** Open one or two files in `tests/` (for example
   `tests/test_core_transfers.py`). Reuse their imports and client setup:
   `from fastapi.testclient import TestClient`, `from services.core import store`,
   `from services.core.main import app`, `client = TestClient(app, raise_server_exceptions=False)`.

4. **Plan the cases before coding.** For each feature write down at least:
   - one happy path,
   - one negative case (use the error table in handbook section 2),
   - one boundary value (for example amount `0.01`, amount `0`, balance exactly equal to the amount).
   Keep the plan in your reply.

5. **Write the test file** in `tests/` with `write_file` (or edit an existing one):
   - Test through endpoints only. Do not import or call internal functions.
   - Reset the store before every test:

     ```python
     @pytest.fixture(autouse=True)
     def _reset_store():
         store.reset()
     ```

   - Name tests `test_<behavior>_<condition>`.
   - Separate the Arrange, Act and Assert sections with comments or blank lines.
   - Use `Decimal` for money comparisons. Assert exact values to the cent.
   - Error responses: assert the status code and `response.json()["error"]["code"]`. Also assert
     there is no `"detail"` key.
   - After a failed money movement, assert that balances are unchanged.
   - Use no real-looking PII or secrets in test data.

6. **Run the tests** with `execute_command`:
   - New file only: `pytest tests/<file>.py -q`
   - Core coverage gate (same as CI): `pytest --cov=services/core --cov-branch --cov-fail-under=85`
   - Limits service gate (same as CI): `pytest tests/test_limits_*.py --cov=services/limits --cov-branch --cov-fail-under=85`

7. **Handle failures honestly.**
   - Test bug: fix the test.
   - Source bug or handbook violation: keep the assertion, do not edit the source, and report it
     (test name, expected vs actual, handbook section).
   - Coverage below 85%: add tests for the uncovered lines shown by `--cov-report=term-missing`.

8. **Report.** Give the files written, the cases covered (happy / negative / boundary), the exact
   pass/fail counts and the coverage figure from the last run. Do not claim results you did not see.
