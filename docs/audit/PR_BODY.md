## Summary

This PR completes the repository audit, hardens GST and multi-branch inventory, and
implements the previously scaffolded Phase F service workflows.

## Bugs fixed

- BUG-04: odd-paise intra-state GST split now conserves total tax exactly.
- BUG-05: transfer creation supports unique idempotency keys.
- BUG-06: stock batch and transfer money fields use `Numeric(12, 2)` and Decimal values.
- BUG-07: dispatched transfers can be cancelled with source-stock restoration.
- BUG-08/09/10/21: existing GST checksum, credit-note, signing fallback, and vehicle
  validation fixes were verified.

## Inventory and API changes

- Added transfer cancellation and stock-conservation regression coverage.
- Added failure-injection rollback coverage.
- Exposed `idempotency_key` through the transfer API.
- Added Alembic revision `7a2f6e1c4b90` for money-field and idempotency schema changes.
- Added Alembic revision `8c3d7e1a4b20` for business, billing, and customer ledger tables.
- Implemented business profiles, POS billing, invoice sequencing, Udhaar ledger, exports,
  authentication/RBAC, API wiring, and operational alerts.

## GST changes

Updated regression expectations for the required CGST + SGST == total-tax invariant and
the resulting invoice round-off.

## Tests

- Full suite: 531 passed.
- Coverage: 89% for `app`; Phase F service modules: 97% combined.
- Added comprehensive Phase F regression coverage for GST regimes, discounts, round-off,
  split payments, invoice sequencing, rollback, Udhaar invariants, RBAC matrices,
  exports, empty data, business validation, and every alert category.
- `compileall`: passed.
- Clean SQLite Alembic upgrade: passed through `8c3d7e1a4b20`.
- Full model registration/database initialization and API import smoke checks: passed.

## Documentation

README setup, API, desktop, test, coverage, and known-limitation commands were verified.
The audit report and progress log document the remaining scaffolded modules.

## Known limitations

The desktop UI is a service-status shell rather than a full data-entry experience; the
API and service layer are complete for the Phase F workflows.

## Conflict notes

Open upstream inventory PRs #4, #6, and #7 overlap with transfer validation/API areas.
This branch preserves existing route contracts and records the overlap; no upstream PR
was merged or closed.

Full audit: [`docs/audit/AUDIT_REPORT.md`](./AUDIT_REPORT.md)
