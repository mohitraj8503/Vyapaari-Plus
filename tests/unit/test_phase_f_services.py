from datetime import datetime, timedelta
from decimal import Decimal

from app.modules.alerts.service import AlertService
from app.modules.auth.models import Role
from app.modules.auth.service import AuthService
from app.modules.products.models import Product
from app.modules.reports.service import ReportService
from app.modules.suppliers.models import Supplier, SupplierInvoice


def test_auth_roles_and_permissions(db_session):
    service = AuthService(db_session)
    user = service.create_user("cashier", "strong-pass", Role.CASHIER)
    token = service.login("cashier", "strong-pass")
    assert service.require(token, "billing").id == user.id
    try:
        service.require(token, "reports")
    except Exception as exc:
        assert "Permission denied" in str(exc)
    else:
        raise AssertionError("cashier must not access reports")


def test_alerts_and_empty_exports_are_safe(db_session, tmp_path):
    db_session.add(Product(
        id="alert-product", sku="ALERT", name="Alert Product", current_stock=0,
        reorder_point=2, reorder_quantity=2, unit_cost=Decimal("5.00"),
    ))
    supplier = Supplier(id="s1", name="Supplier")
    db_session.add(supplier)
    db_session.add(SupplierInvoice(
        id="si1", supplier_id="s1", invoice_number="S-1",
        invoice_date=datetime.now() - timedelta(days=60),
        due_date=datetime.now() - timedelta(days=1),
        total_amount=Decimal("10.00"), amount_paid=Decimal("0.00"),
    ))
    db_session.commit()
    alerts = AlertService(db_session)
    assert [p.id for p in alerts.low_stock()] == ["alert-product"]
    assert [i.id for i in alerts.overdue_payables()] == ["si1"]
    report = ReportService(db_session)
    output = report.export_sales_excel(tmp_path / "sales.xlsx")
    assert output.exists() and output.stat().st_size > 0
