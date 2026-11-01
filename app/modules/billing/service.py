from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from app.core.exceptions import InsufficientStockError, ValidationError
from app.core.money import round_off, round_paise, to_decimal
from app.modules.billing.models import (
    InvoiceCounter,
    PaymentMode,
    SalesInvoice,
    SalesInvoiceLine,
    SalesPayment,
)
from app.modules.billing.repository import BillingRepository
from app.modules.business.service import BusinessService
from app.modules.customers.service import CustomerLedgerService
from app.modules.gst.engine import calculate_line
from app.modules.gst.models import LineItem
from app.modules.gst.place_of_supply import resolve_regime
from app.modules.products.models import Product


class BillingService:
    def __init__(self, db):
        self.db = db
        self.repository = BillingRepository(db)

    def _next_number(self, profile):
        key = f"{profile.id}:{profile.financial_year}"
        counter = self.db.get(InvoiceCounter, key)
        if counter is None:
            counter = InvoiceCounter(id=key, next_number=2)
            number = 1
            self.db.add(counter)
        else:
            number = counter.next_number
            counter.next_number += 1
        value = f"{profile.invoice_prefix}-{profile.financial_year.replace('-', '')}-{number:04d}"
        if len(value) > 16:
            raise ValidationError("Generated invoice number exceeds 16 characters.")
        return value

    def create_bill(self, *, items, place_of_supply=None, customer_id=None,
                    payments=None, idempotency_key=None, bill_discount=Decimal("0.00")):
        if not idempotency_key:
            raise ValidationError("idempotency_key is required.")
        existing = self.repository.by_idempotency_key(idempotency_key)
        if existing:
            return existing
        profile = BusinessService(self.db).get()
        pos = place_of_supply or profile.state_code
        regime = resolve_regime(profile.state_code, pos)
        line_results = []
        taxable_total = Decimal("0.00")
        tax_total = Decimal("0.00")
        try:
            for raw in items:
                product = self.db.get(Product, raw.get("product_id"))
                try:
                    quantity = int(raw.get("quantity", 0))
                except (TypeError, ValueError):
                    raise ValidationError(
                        "Each bill line needs a valid positive quantity and product."
                    ) from None
                if product is None or quantity <= 0:
                    raise ValidationError(
                        "Each bill line needs a valid positive quantity and product."
                    )
                if product.current_stock < quantity:
                    raise InsufficientStockError(product.id, product.current_stock, quantity)
                unit_price = to_decimal(raw.get("unit_price", product.unit_cost), "unit_price")
                discount = to_decimal(raw.get("discount", "0.00"), "discount")
                if discount < 0 or discount > unit_price * quantity:
                    raise ValidationError("Line discount is outside the line value.")
                item = LineItem(
                    description=product.name, hsn_sac=raw.get("hsn_sac", "0000"),
                    quantity=quantity, unit_price=unit_price, discount=discount,
                    gst_rate=raw.get("gst_rate", "0"),
                )
                tax = calculate_line(item, regime)
                product.current_stock -= quantity
                line_results.append((product, item, tax))
                taxable_total += tax.taxable_value
                tax_total += tax.cgst + tax.sgst + tax.igst + tax.cess
            bill_discount = to_decimal(bill_discount, "bill_discount")
            if bill_discount < 0 or bill_discount > taxable_total:
                raise ValidationError("Bill discount is outside the taxable total.")
            if bill_discount:
                original_taxable = taxable_total
                adjusted_lines = []
                remaining_discount = bill_discount
                for index, (product, item, tax) in enumerate(line_results):
                    if index == len(line_results) - 1:
                        allocation = remaining_discount
                    else:
                        allocation = round_paise(
                            bill_discount * tax.taxable_value / original_taxable
                        )
                        remaining_discount -= allocation
                    adjusted_item = item.model_copy(
                        update={"discount": item.discount + allocation}
                    )
                    adjusted_tax = calculate_line(adjusted_item, regime)
                    adjusted_lines.append((product, adjusted_item, adjusted_tax))
                line_results = adjusted_lines
                tax_total = sum(
                    (tax.cgst + tax.sgst + tax.igst + tax.cess for _, _, tax in line_results),
                    Decimal("0.00"),
                )
                taxable_total = sum(
                    (tax.taxable_value for _, _, tax in line_results),
                    Decimal("0.00"),
                )
            taxable_total = round_paise(taxable_total)
            total_before_round = taxable_total + tax_total
            total, adjustment = round_off(total_before_round)
            invoice = SalesInvoice(
                id=str(uuid4()), business_id=profile.id, customer_id=customer_id,
                invoice_number=self._next_number(profile), financial_year=profile.financial_year,
                invoice_date=date.today(), place_of_supply=pos, taxable_total=taxable_total,
                tax_total=tax_total, round_off=adjustment, total=total,
                idempotency_key=idempotency_key,
            )
            self.db.add(invoice)
            for product, item, tax in line_results:
                self.db.add(SalesInvoiceLine(
                    id=str(uuid4()), invoice=invoice, product_id=product.id,
                    description=product.name, quantity=int(item.quantity), unit_price=item.unit_price,
                    discount=item.discount, taxable_value=tax.taxable_value,
                    tax=tax.cgst + tax.sgst + tax.igst + tax.cess,
                    total=tax.line_total, gst_rate=item.gst_rate,
                ))
            paid = Decimal("0.00")
            for raw_payment in payments or []:
                mode = PaymentMode(raw_payment["mode"])
                amount = to_decimal(raw_payment["amount"], "payment amount")
                if amount <= 0:
                    raise ValidationError("Payment amount must be positive.")
                paid += amount
                self.db.add(SalesPayment(id=str(uuid4()), invoice=invoice, mode=mode, amount=amount))
            if paid > total:
                raise ValidationError("Payments cannot exceed invoice total.")
            self.db.flush()
            if customer_id and paid < total:
                CustomerLedgerService(self.db).record_sale(customer_id, total - paid, invoice.id)
            self.db.commit()
            self.db.refresh(invoice)
            return invoice
        except Exception:
            self.db.rollback()
            raise

    def cancel_bill(self, invoice_id: str):
        invoice = self.db.get(SalesInvoice, invoice_id)
        if invoice is None:
            raise ValidationError("Invoice not found.")
        if invoice.cancelled_at:
            return invoice
        for line in invoice.lines:
            product = self.db.get(Product, line.product_id)
            product.current_stock += line.quantity
        invoice.cancelled_at = datetime.utcnow()
        if invoice.customer_id:
            CustomerLedgerService(self.db).record_reversal(invoice.customer_id, invoice.total, invoice.id)
        self.db.commit()
        return invoice
