# Inventory: Multi-Store Stock Transfer (TTI000044)

Module: `app/modules/inventory`

## Lifecycle

`DRAFT -> DISPATCHED -> IN_TRANSIT -> RECEIVED -> RECONCILED / DISPUTED`

| Step | Method | Guard |
|---|---|---|
| Create | `create_transfer_request` | validates branches, items, quantities |
| Dispatch | `dispatch_transfer` | only from `DRAFT`; deducts source stock; creates challan and gate pass |
| In transit | `start_transit` | only after dispatch |
| Receive | `receive_and_record_delivery` | only from `IN_TRANSIT`; good + damaged <= dispatched |
| Reconcile | `MultiBranchReconciliationEngine` | variance = dispatched - good received |

Every state change writes a `CarrierLog` entry (timestamped audit trail).

## Idempotent creation

`create_transfer_request(..., idempotency_key="<client key>")`

- Same key + same payload: returns the original transfer, no duplicate rows.
- Same key + different payload: `ValidationError`.
- Blank, non-string or >100 char key: `ValidationError`.
- Concurrent duplicates: the unique constraint on `idempotency_key` is
  caught and the original transfer is returned.
- No key: behaves exactly as before.

## Concurrency and consistency

Stock rows are read with `with_for_update()` during dispatch. On SQLite
(the desktop default) row-level locks are not enforced by the database;
writes are serialized per connection. On PostgreSQL/MySQL the same code
takes real row locks. Status guards also prevent a transfer from being
dispatched or received twice.

## Existing databases

`create_all` does not alter existing tables. For an existing database file:

```sql
ALTER TABLE stock_transfers ADD COLUMN idempotency_key VARCHAR(100);
CREATE UNIQUE INDEX ix_stock_transfers_idempotency_key
    ON stock_transfers (idempotency_key);
```

## Tests

## Scope note

This repository is a Windows desktop application with a service layer and
no HTTP server, so the transfer operations are exposed as service methods
rather than REST endpoints.
