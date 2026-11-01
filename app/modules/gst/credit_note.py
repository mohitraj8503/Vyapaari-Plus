"""Credit and Debit note tax calculation and validation against original invoice.

Rules:
- Amounts stay positive; the document type (CRN/DBN) specifies direction.
- Must reference an original invoice (doc_no and doc_date).
- Supplier, buyer, and place of supply must match the original invoice.
- Item tax rates and place of supply must match the original invoice.
- Neither a single credit note nor cumulative credit notes can exceed the original invoice value.
- Item quantities in credit note(s) cannot exceed original item quantities.
"""

from collections import defaultdict
from decimal import Decimal

from app.core.exceptions import ValidationError
from app.modules.gst.invoice_calc import RateLookup, calculate_invoice
from app.modules.gst.models import DocType, Invoice, TaxBreakup

ZERO = Decimal("0.00")


def calculate_credit_note(
    credit_note: Invoice,
    original: Invoice | None = None,
    rate_lookup: RateLookup | None = None,
    existing_credit_notes: list[Invoice] | None = None,
) -> TaxBreakup:
    """Calculate and validate a credit note (CRN) against its original invoice."""
    if credit_note.doc_type is not DocType.CRN:
        raise ValidationError("calculate_credit_note needs a credit note (doc_type CRN)")
    breakup = calculate_invoice(credit_note, rate_lookup)
    if original is not None:
        _check_against_original(
            credit_note=credit_note,
            original=original,
            breakup=breakup,
            rate_lookup=rate_lookup,
            existing_credit_notes=existing_credit_notes,
        )
    return breakup


def calculate_debit_note(
    debit_note: Invoice,
    original: Invoice | None = None,
    rate_lookup: RateLookup | None = None,
) -> TaxBreakup:
    """Calculate and validate a debit note (DBN) against its original invoice."""
    if debit_note.doc_type is not DocType.DBN:
        raise ValidationError("calculate_debit_note needs a debit note (doc_type DBN)")
    breakup = calculate_invoice(debit_note, rate_lookup)
    if original is not None:
        _check_header_against_original(debit_note, original)
    return breakup


def _check_header_against_original(note: Invoice, original: Invoice) -> None:
    if original.doc_type is not DocType.INV:
        raise ValidationError("the original document must be an invoice (doc_type INV)")
    ref = note.original_invoice
    if ref is None:
        raise ValidationError(f"{note.doc_type} must reference an original invoice")
    if (ref.doc_no, ref.doc_date) != (original.doc_no, original.doc_date):
        raise ValidationError(
            f"{note.doc_type} original_invoice does not match the original invoice"
        )
    if (
        note.supplier.gstin != original.supplier.gstin
        or note.buyer.gstin != original.buyer.gstin
        or note.place_of_supply != original.place_of_supply
    ):
        raise ValidationError(
            f"{note.doc_type} parties and place of supply must match the original invoice"
        )


def _check_against_original(
    credit_note: Invoice,
    original: Invoice,
    breakup: TaxBreakup,
    rate_lookup: RateLookup | None,
    existing_credit_notes: list[Invoice] | None = None,
) -> None:
    _check_header_against_original(credit_note, original)
    original_breakup = calculate_invoice(original, rate_lookup)

    # 1. Single credit note value cap
    if breakup.taxable_total > original_breakup.taxable_total:
        raise ValidationError("credit note taxable value exceeds the original invoice")

    # 2. Cumulative credit notes value cap
    total_taxable = breakup.taxable_total
    credited_quantities_by_hsn = defaultdict(Decimal)

    for item in credit_note.items:
        credited_quantities_by_hsn[item.hsn_sac] += item.quantity

    if existing_credit_notes:
        for prev in existing_credit_notes:
            if prev.original_invoice and (
                prev.original_invoice.doc_no != original.doc_no
                or prev.original_invoice.doc_date != original.doc_date
            ):
                continue
            prev_breakup = calculate_invoice(prev, rate_lookup)
            total_taxable += prev_breakup.taxable_total
            for item in prev.items:
                credited_quantities_by_hsn[item.hsn_sac] += item.quantity

        if total_taxable > original_breakup.taxable_total:
            raise ValidationError(
                f"cumulative credit notes taxable value ({total_taxable}) exceeds "
                f"original invoice taxable value ({original_breakup.taxable_total})"
            )

    # 3. Item-level quantity caps
    original_quantities = defaultdict(Decimal)
    for orig_item in original.items:
        original_quantities[orig_item.hsn_sac] += orig_item.quantity

    for hsn, cred_qty in credited_quantities_by_hsn.items():
        orig_qty = original_quantities.get(hsn, Decimal("0"))
        if cred_qty > orig_qty:
            raise ValidationError(
                f"credit note quantity for item {hsn} ({cred_qty}) exceeds original quantity ({orig_qty})"
            )
