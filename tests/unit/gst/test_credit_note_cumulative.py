"""Regression tests for cumulative credit notes and debit notes [BUG-09]."""

from datetime import date
from decimal import Decimal
import pytest

from app.core.exceptions import ValidationError
from app.modules.gst.credit_note import calculate_credit_note, calculate_debit_note
from app.modules.gst.models import Invoice, LineItem, OriginalInvoiceRef, Party

SUPPLIER_GSTIN = "24AAACC1206D1ZM"
BUYER_GSTIN = "27AAACB1234F1Z5"


def make_invoice(items=None, **overrides):
    supplier = Party(name="Seller", state_code="24", gstin=SUPPLIER_GSTIN)
    buyer = Party(name="Buyer", state_code="27", gstin=BUYER_GSTIN)
    if items is None:
        items = [
            LineItem(
                description="Item A",
                hsn_sac="1006",
                quantity=10,
                unit_price="100.00",
                gst_rate="18",
            )
        ]
    data = {
        "doc_no": "INV-2026-001",
        "doc_date": date(2026, 10, 1),
        "supplier": supplier,
        "buyer": buyer,
        "place_of_supply": "27",
        "supply_type": "B2B",
        "items": items,
    }
    data.update(overrides)
    return Invoice(**data)


def make_credit(items=None, doc_no="CN-001", **overrides):
    ref = OriginalInvoiceRef(doc_no="INV-2026-001", doc_date=date(2026, 10, 1))
    if items is None:
        items = [
            LineItem(
                description="Item A",
                hsn_sac="1006",
                quantity=4,
                unit_price="100.00",
                gst_rate="18",
            )
        ]
    data = {
        "doc_type": "CRN",
        "doc_no": doc_no,
        "doc_date": date(2026, 10, 10),
        "original_invoice": ref,
        "items": items,
    }
    data.update(overrides)
    return make_invoice(**data)


def test_cumulative_credit_notes_cannot_exceed_original_value():
    original = make_invoice()  # 10 units @ 100 = 1000 taxable
    cn1 = make_credit(items=[LineItem(description="Item A", hsn_sac="1006", quantity=6, unit_price="100.00", gst_rate="18")], doc_no="CN-001")
    cn2 = make_credit(items=[LineItem(description="Item A", hsn_sac="1006", quantity=5, unit_price="100.00", gst_rate="18")], doc_no="CN-002")

    # cn1 alone is valid (600 <= 1000)
    calculate_credit_note(cn1, original=original)

    # cn2 with existing cn1 fails (600 + 500 = 1100 > 1000)
    with pytest.raises(ValidationError, match="cumulative credit notes taxable value"):
        calculate_credit_note(cn2, original=original, existing_credit_notes=[cn1])


def test_cumulative_credit_notes_exact_match_allowed():
    original = make_invoice()  # 10 units @ 100 = 1000 taxable
    cn1 = make_credit(items=[LineItem(description="Item A", hsn_sac="1006", quantity=6, unit_price="100.00", gst_rate="18")], doc_no="CN-001")
    cn2 = make_credit(items=[LineItem(description="Item A", hsn_sac="1006", quantity=4, unit_price="100.00", gst_rate="18")], doc_no="CN-002")

    breakup2 = calculate_credit_note(cn2, original=original, existing_credit_notes=[cn1])
    assert breakup2.taxable_total == Decimal("400.00")


def test_credit_note_item_quantity_exceeds_original():
    original = make_invoice()  # 10 units
    cn = make_credit(items=[LineItem(description="Item A", hsn_sac="1006", quantity=11, unit_price="50.00", gst_rate="18")], doc_no="CN-001")
    # Even though 11 * 50 = 550 <= 1000, quantity 11 > 10
    with pytest.raises(ValidationError, match="exceeds original quantity"):
        calculate_credit_note(cn, original=original)


def test_calculate_debit_note_valid():
    original = make_invoice()
    ref = OriginalInvoiceRef(doc_no="INV-2026-001", doc_date=date(2026, 10, 1))
    dbn = make_invoice(
        doc_type="DBN",
        doc_no="DN-001",
        original_invoice=ref,
        items=[LineItem(description="Item A price increase", hsn_sac="1006", quantity=10, unit_price="10.00", gst_rate="18")]
    )
    breakup = calculate_debit_note(dbn, original=original)
    assert breakup.taxable_total == Decimal("100.00")
    assert breakup.igst_total == Decimal("18.00")
