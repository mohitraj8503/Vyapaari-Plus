# Vyapaari+ Inventory Engine

## 1. Overview

The inventory engine supports inter-branch stock transfers, batch-level stock accounting, delivery documents, carrier tracking, receipt recording, discrepancy reconciliation, and reconciliation approval history.

The implementation uses SQLAlchemy ORM and exposes selected operations through a FastAPI application in `app/api.py`.

The Python service layer contains additional operations that are not currently exposed as HTTP endpoints. This distinction is important when integrating API clients.

**Implementation reference:** Consolidated inventory engine currently available on `upstream/main`, including merged PR #5. API contracts must be rechecked after related inventory pull requests are merged.

## 2. Architecture

The principal implementation files are:

| File | Responsibility |
|---|---|
| `app/api.py` | FastAPI routes, request validation, response serialization, and HTTP error mapping. |
| `app/modules/inventory/models.py` | SQLAlchemy inventory models and database constraints. |
| `app/modules/inventory/service.py` | `InventoryService` facade for transfer and reconciliation services. |
| `app/modules/inventory/stock_transfer.py` | Transfer creation, dispatch, transit, receipt, delivery documents, and carrier tracking. |
| `app/modules/inventory/reconciliation.py` | Variance calculation, reconciliation, dispute decisions, and approval history. |

The FastAPI application uses `SessionLocal` to obtain database sessions.

## 3. Data Models

| Model | Purpose |
|---|---|
| `Branch` | Identifies branches and warehouses. |
| `StoreLocations` | Represents a physical store or warehouse location associated with a branch. |
| `StockBatch` | Stores product batches, quantities, prices, and optional expiry dates by branch. |
| `StockTransfer` | Tracks transfer identity, source and destination branches, status, documents, and delivery information. |
| `TransferItem` | Records product, batch, dispatched quantity, good received quantity, damaged quantity, and unit cost. |
| `ReconciliationLog` | Stores aggregate transfer quantities, variance, transit loss value, resolution status, and remarks. |
| `ReconciliationApproval` | Records approval or rejection decisions for disputed reconciliations. |
| `InTransitLog` | Stores transfer events with a unique idempotency key. |
| `CarrierLog` | Records carrier tracking and delivery events. |

### 3.1 Database Constraints

The models define constraints including:

- Source and destination branches must differ.
- Transfer numbers are unique.
- Transfer-item quantities and unit costs cannot be negative.
- Good received plus damaged quantity cannot exceed dispatched quantity.
- Each transfer can have only one reconciliation log.
- Reconciliation variance must equal dispatched units minus good received units.
- Reconciliation resolution status must be `PENDING` or `RESOLVED`.
- Reconciliation approval decisions must be `APPROVED` or `REJECTED`.
- `InTransitLog.idempotency_key` must be unique.

The unique idempotency-key constraint supports event uniqueness at the database level. It does not establish that the HTTP API supports idempotency keys or replay of previously successful responses.

## 4. Transfer Lifecycle

The `TransferStatus` enum defines:

| Status | Meaning |
|---|---|
| `DRAFT` | Transfer request has been created. |
| `DISPATCHED` | Source stock has been deducted and the transfer dispatched. |
| `IN_TRANSIT` | Transfer has entered transit. |
| `RECEIVED` | Delivery quantities have been recorded. |
| `RECONCILED` | Reconciliation is complete or a dispute has been approved. |
| `DISPUTED` | Reconciliation found a discrepancy awaiting resolution. |

The normal service-layer workflow is:

```text
DRAFT
  |
  | dispatch_transfer()
  v
DISPATCHED
  |
  | start_transit()
  v
IN_TRANSIT
  |
  | receive_and_record_delivery()
  v
RECEIVED
  |
  | reconcile_transfer()
  +--------------------+
  |                    |
  | No variance        | Variance exists
  v                    v
RECONCILED           DISPUTED
                       |
                       | record_approval(APPROVED)
                       v
                    RECONCILED
```

A rejected reconciliation remains disputed. Rejection requires remarks.

### 4.1 Transfer Creation

`create_transfer_request()` validates the source and destination branches, requires at least one transfer item, and checks that dispatched quantities are positive integers.

It creates a `DRAFT` transfer and records a `TRANSFER_CREATED` carrier event.

### 4.2 Dispatch

`dispatch_transfer()` operates on a `DRAFT` transfer.

It:

1. Selects a matching source stock batch with enough quantity for the complete transfer item.
2. Deducts the dispatched quantity from that batch.
3. Records the selected batch number on the transfer item.
4. Generates a delivery challan and gate pass if they do not already exist.
5. Updates the transfer to `DISPATCHED`.
6. Records a carrier event.

The implementation does not split a single transfer item across multiple source batches when selecting stock.

### 4.3 Transit and Tracking

`start_transit()` changes a `DISPATCHED` transfer to `IN_TRANSIT`.

The service also provides:

- `generate_delivery_documents()`
- `update_carrier_tracking()`
- `record_carrier_event()`
- `get_tracking_history()`

These methods are available in the Python service layer but are not exposed by the verified `app/api.py` routes.

### 4.4 Receipt

`receive_and_record_delivery()` requires the transfer to be `IN_TRANSIT`.

The receipt must include exactly one entry for every transfer item. Duplicate item IDs, unknown item IDs, missing item entries, negative quantities, and quantities exceeding dispatched stock are rejected.

Only good received units are added to destination stock. The service updates an existing matching destination batch or creates one using the selected batch number.

Damaged and missing units are not added to usable destination stock.

## 5. HTTP API

The FastAPI application is defined in `app/api.py`.

### 5.1 Endpoint Summary

| Method | Route | Purpose | Success status |
|---|---|---|---|
| `GET` | `/health` | Health check | `200` |
| `POST` | `/transfers` | Create a transfer | `201` |
| `POST` | `/transfers/{transfer_id}/dispatch` | Dispatch a transfer | `200` |
| `POST` | `/transfers/{transfer_id}/receive` | Record delivery quantities | `200` |
| `POST` | `/transfers/{transfer_id}/reconcile` | Reconcile a received transfer | `200` |

**Important:** The verified API does not expose a route for `start_transit()`. Because receipt requires `IN_TRANSIT`, the currently exposed HTTP routes alone do not provide a complete transfer workflow.

### 5.2 Create Transfer

**Endpoint:** `POST /transfers`

Example request:

```json
{
  "source_branch_id": "BR001",
  "destination_branch_id": "BR002",
  "items": [
    {
      "product_id": "PROD001",
      "product_name": "Rice",
      "quantity_dispatched": 10,
      "unit_cost": 50.0,
      "batch_number": "BATCH001"
    }
  ],
  "dispatched_by": "store_manager",
  "notes": "Inter-branch stock transfer"
}
```

Required request fields:

| Field | Type | Validation |
|---|---|---|
| `source_branch_id` | string | Nonempty |
| `destination_branch_id` | string | Nonempty |
| `items` | array | At least one item |
| `items[].product_id` | string | Nonempty |
| `items[].quantity_dispatched` | integer | Greater than zero |

Optional fields:

| Field | Type | Default |
|---|---|---|
| `items[].product_name` | string | `"Unknown Product"` |
| `items[].unit_cost` | number | `0.0` |
| `items[].batch_number` | string or null | `null` |
| `dispatched_by` | string or null | `null` |
| `notes` | string or null | `null` |

`unit_cost` must be nonnegative.

The API returns a serialized transfer with HTTP status `201`.

Example responses throughout this document are illustrative. Successful execution also depends on database records and service-layer validation.

### 5.3 Dispatch Transfer

**Endpoint:** `POST /transfers/{transfer_id}/dispatch`

Example request:

```json
{
  "vehicle_number": "MH20AB1234",
  "driver_contact": "9876543210"
}
```

Both fields are optional.

Dispatch requires a `DRAFT` transfer and sufficient stock in a matching source batch.

The response uses the transfer response structure described in Section 5.5.

### 5.4 Receive Transfer

**Endpoint:** `POST /transfers/{transfer_id}/receive`

Example request:

```json
{
  "items": [
    {
      "item_id": "EXISTING_TRANSFER_ITEM_ID",
      "quantity_received": 8,
      "quantity_damaged": 1
    }
  ],
  "received_by": "receiving_manager"
}
```

| Field | Type | Validation |
|---|---|---|
| `items` | array | Must contain every transfer item exactly once at the service layer |
| `items[].item_id` | string | Nonempty; must identify a transfer item |
| `items[].quantity_received` | integer | Nonnegative |
| `items[].quantity_damaged` | integer | Nonnegative; defaults to `0` |
| `received_by` | string or null | Optional |

The sum of good received and damaged quantities cannot exceed the dispatched quantity.

The transfer must already be `IN_TRANSIT`.

### 5.5 Transfer Response

Create, dispatch, and receive return the following response fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | Transfer ID |
| `transfer_number` | string | Generated transfer reference |
| `gate_pass_number` | string or null | Generated gate pass reference |
| `source_branch_id` | string | Source branch |
| `destination_branch_id` | string | Destination branch |
| `status` | string | Transfer status |
| `items` | array | Transfer items and quantities |

Each response item includes:

`item_id`, `product_id`, `product_name`, `quantity_dispatched`, `quantity_received`, `quantity_damaged`, and `unit_cost`.

Example response shape:

```json
{
  "id": "TRANSFER_ID",
  "transfer_number": "TRF-EXAMPLE",
  "gate_pass_number": null,
  "source_branch_id": "BR001",
  "destination_branch_id": "BR002",
  "status": "DRAFT",
  "items": [
    {
      "item_id": "TRANSFER_ITEM_ID",
      "product_id": "PROD001",
      "product_name": "Rice",
      "quantity_dispatched": 10,
      "quantity_received": 0,
      "quantity_damaged": 0,
      "unit_cost": 50.0
    }
  ]
}
```

### 5.6 Reconcile Transfer

**Endpoint:** `POST /transfers/{transfer_id}/reconcile`

This endpoint accepts the following **query parameters**, not a JSON request body:

| Parameter | Type | API default |
|---|---|---|
| `reconciled_by` | string | `"api"` |
| `resolution_status` | string | `"RESOLVED"` |
| `remarks` | string or null | `null` |

Allowed resolution statuses are `PENDING` and `RESOLVED`.

**Important implementation detail:** The HTTP endpoint defaults to `RESOLVED`, while the reconciliation service rejects `RESOLVED` if the transfer has a nonzero variance.

For transfers with damaged or missing units, explicitly use:

```http
POST /transfers/{transfer_id}/reconcile?resolution_status=PENDING
```

A zero-variance transfer can be reconciled as `RESOLVED`.

The endpoint returns:

| Field | Description |
|---|---|
| `transfer_id` | Reconciled transfer ID |
| `total_dispatched_units` | Total dispatched quantity |
| `total_received_units` | Total good received quantity |
| `variance_units` | Dispatched minus good received |
| `total_transit_loss_value` | Calculated damaged and missing stock value |
| `resolution_status` | `PENDING` or `RESOLVED` |
| `remarks` | Remarks and generated reconciliation summary |

### 5.7 Errors

The API maps selected service exceptions to HTTP responses:

| HTTP status | Cause |
|---|---|
| `400` | Service `ValidationError` |
| `404` | Service `EntityNotFoundError` |
| `409` | Service `InsufficientStockError` |
| `422` | FastAPI/Pydantic request validation failure |

Other unhandled failures are not assigned custom HTTP mappings by the verified API implementation.

## 6. Stock Accounting and Reconciliation

For each transfer item:

```text
Missing units = Dispatched - Good received - Damaged

Variance units = Dispatched - Good received

Transit loss value = (Damaged + Missing) × Unit cost
```

Aggregate reconciliation figures are calculated across all transfer items.

For example, suppose a transfer item has:

| Quantity | Value |
|---|---:|
| Dispatched | 10 |
| Good received | 8 |
| Damaged | 1 |
| Missing | 1 |
| Unit cost | 50 |

The resulting figures are:

- Variance: `10 - 8 = 2` units
- Transit loss value: `(1 + 1) × 50 = 100`

The source stock is deducted at dispatch. Good received stock is added at receipt.

Reconciliation calculates and records the discrepancy; it does not perform a second stock adjustment.

### 6.1 Reconciliation Eligibility

The service permits first-time reconciliation when:

- The transfer is `RECEIVED` or `DISPUTED`.
- No reconciliation log already exists.
- The transfer contains items.

A transfer cannot be reconciled twice.

### 6.2 Dispute Approval

A nonzero variance produces a `DISPUTED` transfer with a pending reconciliation.

The Python service method `record_approval()` supports:

| Decision | Result |
|---|---|
| `APPROVED` | Resolution becomes `RESOLVED`; transfer becomes `RECONCILED`. |
| `REJECTED` | Transfer remains disputed; remarks are required. |

Approval and rejection are permitted only for disputed transfers with pending reconciliation.

The service preserves approval history through `ReconciliationApproval`.

**HTTP limitation:** The verified `app/api.py` does not expose an approval endpoint.

## 7. Transactions, Concurrency, and Idempotency

Transfer creation, document generation, dispatch, transit updates, receipt, and reconciliation use SQLAlchemy database transactions with commit and rollback handling.

Selected queries use `with_for_update()`.

The effectiveness of row-level locking depends on the database backend. In particular, using `with_for_update()` does not establish effective row-level locking on SQLite.

The service rejects invalid state transitions, including repeated dispatch or receipt after a transfer has advanced.

The `InTransitLog` model contains a unique `idempotency_key`, but the verified HTTP routes do not accept idempotency keys or implement successful-response replay. These are separate concerns and should not be described as complete HTTP idempotency support.

Production concurrency guarantees and timeout recovery require backend-specific testing.

## 8. Database Migrations

The currently inspected `upstream/main` tree includes tracked Alembic migration infrastructure, including:

- `migrations/README`
- `migrations/env.py`
- `migrations/script.py.mako`
- `migrations/versions/1180d7f53b6c_add_inventory_transfer_tables.py`
- `migrations/versions/4b6a0d2c9f71_repair_inventory_transfer_schema.py`
- `migrations/versions/692fa2e1bbdd_add_store_locations_table.py`

These files establish that migration scripts exist in the merged repository.

Their presence alone does not establish that every migration has been successfully applied to a particular database. The migration configuration, revision chain, and target database should be verified before running upgrades.

## 9. Automated Tests

Run the test suite from the repository root:

```bash
python -m pytest -q
```

Inventory-related tests include:

```text
tests/unit/test_stock_transfer.py
```

The test suite should be rerun after integrating the final inventory engine changes.

A previously reported passing result is not a substitute for validation against the final merged code.

## 10. Known Limitations and Integration Notes

The following limitations apply to the currently verified implementation:

1. **Incomplete HTTP lifecycle:** `start_transit()` exists in the Python service layer but has no corresponding route in `app/api.py`. Receipt requires `IN_TRANSIT`.
2. **Reconciliation default mismatch:** The HTTP reconciliation route defaults to `RESOLVED`, which is rejected for transfers with a nonzero variance. Clients must specify `resolution_status=PENDING` for discrepancies.
3. **Service-only capabilities:** Carrier tracking, delivery-document generation, reconciliation approvals, and approval-history retrieval are not exposed by the verified HTTP routes.
4. **No verified HTTP idempotency contract:** The event model has a unique idempotency key, but the exposed routes do not implement idempotency-key request handling and response replay.
5. **Batch selection limitation:** Dispatch requires a single matching source batch to satisfy each complete transfer item.
6. **Backend-dependent concurrency:** Row-locking behavior and concurrent-write safety require verification on the deployment database.
7. **Migration verification:** Tracked Alembic revisions exist, but their successful application and compatibility with every deployment database have not been established.

## 11. Synchronization Checklist

Before considering this document final:

- Confirm the merge status of related inventory PRs #6 and #7.
- Compare the final merged `app/api.py` against the endpoint and schema tables above.
- Recheck model names, fields, constraints, and migration revisions.
- Recheck transfer lifecycle and reconciliation approval behavior.
- Run the test suite against the final merged code.
- Update examples if the consolidated API contracts change.
- Rebase the documentation PR onto the appropriate updated base branch.

This document describes the verified implementation, not unmerged or proposed functionality.