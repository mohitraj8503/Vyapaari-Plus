from decimal import Decimal

import pytest

from app.core.exceptions import InsufficientStockError, ValidationError
from app.modules.billing.models import PaymentMode
from app.modules.billing.service import BillingService
from app.modules.business.service import BusinessService
from app.modules.customers.models import CustomerLedgerEntry
from app.modules.customers.service import CustomerLedgerService
from app.modules.products.models import Product
from app.modules.suppliers.models import Supplier  # noqa: F401


def test_business_profile_is_validated_and_updated(db_session):
    service = BusinessService(db_session)
    profile = service.create_or_update(
        name="Demo Retail", state_code="24", address="Market Road",
        gstin="24AAACC1206D1ZM", invoice_prefix="DR",
    )
    assert profile.financial_year.startswith("2026")
    updated = service.create_or_update(
        name="Demo Retail Updated", state_code="24", address="New Road",
        gstin="24AAACC1206D1ZM", invoice_prefix="DR",
    )
    assert updated.id == profile.id
    assert updated.name == "Demo Retail Updated"

    with pytest.raises(ValidationError):
        service.create_or_update(
            name="Bad", state_code="27", address="x",
            gstin="24AAACC1206D1ZM",
        )


def test_bill_is_atomic_idempotent_and_deducts_stock(db_session):
    BusinessService(db_session).create_or_update(
        name="Demo Retail", state_code="24", address="Market Road",
        gstin="24AAACC1206D1ZM", invoice_prefix="DR",
    )
    product = Product(
        id="p1", sku="RICE-1", name="Rice", current_stock=5,
        reorder_point=1, reorder_quantity=5, unit_cost=Decimal("10.00"),
    )
    db_session.add(product)
    db_session.commit()
    service = BillingService(db_session)
    invoice = service.create_bill(
        items=[{"product_id": "p1", "quantity": 2, "unit_price": "20.00", "gst_rate": "5", "hsn_sac": "1001"}],
        payments=[{"mode": PaymentMode.CASH, "amount": "42.00"}],
        idempotency_key="bill-1",
    )
    assert invoice.total == Decimal("42.00")
    assert db_session.get(Product, "p1").current_stock == 3
    assert service.create_bill(
        items=[{"product_id": "p1", "quantity": 2, "unit_price": "20.00", "gst_rate": "5", "hsn_sac": "1001"}],
        idempotency_key="bill-1",
    ).id == invoice.id

    with pytest.raises(InsufficientStockError):
        service.create_bill(
            items=[{"product_id": "p1", "quantity": 99, "unit_price": "20.00", "gst_rate": "5", "hsn_sac": "1001"}],
            idempotency_key="bill-2",
        )
    assert db_session.get(Product, "p1").current_stock == 3


def test_customer_ledger_balance_is_sum_of_entries(db_session):
    customer = CustomerLedgerService(db_session).create_customer(
        "A Customer", credit_limit=Decimal("500.00")
    )
    service = CustomerLedgerService(db_session)
    service.record_sale(customer.id, Decimal("120.00"))
    db_session.commit()
    service.record_payment(customer.id, Decimal("20.00"))
    assert service.balance(customer.id) == Decimal("100.00")
    entries = db_session.query(CustomerLedgerEntry).filter(
        CustomerLedgerEntry.customer_id == customer.id
    ).all()
    assert service.balance(customer.id) == sum((e.signed_amount for e in entries), Decimal("0.00"))
    service.record_reversal(customer.id, Decimal("120.00"))
    db_session.commit()
    assert service.balance(customer.id) == Decimal("-20.00")
