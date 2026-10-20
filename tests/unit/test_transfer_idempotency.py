import pytest

from app.core.exceptions import ValidationError
from app.modules.inventory.models import Branch, StockTransfer
from app.modules.inventory.stock_transfer import StockTransferService


def _setup(db):
    db.add_all(
        [
            Branch(id="br-a", name="Warehouse A", code="WA"),
            Branch(id="br-b", name="Store B", code="SB"),
        ]
    )
    db.commit()
    return StockTransferService(db)


def _items(qty=5):
    return [
        {
            "product_id": "p1",
            "product_name": "Widget",
            "batch_number": "B1",
            "quantity_dispatched": qty,
            "unit_cost": 10.0,
        }
    ]


def test_same_key_returns_same_transfer(db_session):
    svc = _setup(db_session)
    first = svc.create_transfer_request(
        "br-a", "br-b", _items(), idempotency_key="k1"
    )
    retry = svc.create_transfer_request(
        "br-a", "br-b", _items(), idempotency_key="k1"
    )
    assert retry.id == first.id
    assert db_session.query(StockTransfer).count() == 1


def test_different_keys_create_different_transfers(db_session):
    svc = _setup(db_session)
    a = svc.create_transfer_request("br-a", "br-b", _items(), idempotency_key="k1")
    b = svc.create_transfer_request("br-a", "br-b", _items(), idempotency_key="k2")
    assert a.id != b.id


def test_same_key_with_different_payload_is_rejected(db_session):
    svc = _setup(db_session)
    svc.create_transfer_request("br-a", "br-b", _items(5), idempotency_key="k1")
    with pytest.raises(ValidationError):
        svc.create_transfer_request(
            "br-a", "br-b", _items(9), idempotency_key="k1"
        )
    assert db_session.query(StockTransfer).count() == 1


@pytest.mark.parametrize("bad_key", ["", "   ", 123, "x" * 101])
def test_invalid_key_is_rejected(db_session, bad_key):
    svc = _setup(db_session)
    with pytest.raises(ValidationError):
        svc.create_transfer_request(
            "br-a", "br-b", _items(), idempotency_key=bad_key
        )


def test_requests_without_key_still_work(db_session):
    svc = _setup(db_session)
    a = svc.create_transfer_request("br-a", "br-b", _items())
    b = svc.create_transfer_request("br-a", "br-b", _items())
    assert a.id != b.id
