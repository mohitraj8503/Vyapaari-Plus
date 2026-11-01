"""Regression tests for odd-paise GST calculation and CGST/SGST splitting [BUG-04]."""

from decimal import Decimal
import pytest

from app.modules.gst.engine import calculate_line
from app.modules.gst.models import LineItem
from app.modules.gst.place_of_supply import Regime


def make_item(quantity="1", unit_price="10.00", gst_rate="18", discount="0"):
    return LineItem(
        description="Odd paise test item",
        hsn_sac="1006",
        quantity=quantity,
        unit_price=unit_price,
        gst_rate=gst_rate,
        discount=discount,
    )


@pytest.mark.parametrize(
    "price, rate",
    [
        ("10.10", "5"),
        ("10.15", "5"),
        ("33.33", "12"),
        ("17.77", "18"),
        ("99.99", "28"),
        ("1.05", "3"),
        ("2.03", "5"),
        ("15.55", "18"),
    ],
)
def test_cgst_plus_sgst_strictly_equals_total_tax(price, rate):
    item = make_item(unit_price=price, gst_rate=rate)
    line_intra = calculate_line(item, Regime.INTRA)
    line_inter = calculate_line(item, Regime.INTER)

    # In INTRA, CGST + SGST must exactly equal the total tax (which equals IGST in INTER)
    assert line_intra.cgst + line_intra.sgst == line_inter.igst
    assert line_intra.tax_total == line_inter.tax_total
    assert line_intra.line_total == line_inter.line_total


def test_odd_paise_split_difference_at_most_one_paisa():
    item = make_item(unit_price="10.10", gst_rate="5")
    line = calculate_line(item, Regime.INTRA)

    # Total tax is 0.51 paise. Split is 0.26 and 0.25
    assert line.cgst == Decimal("0.26")
    assert line.sgst == Decimal("0.25")
    assert line.cgst + line.sgst == Decimal("0.51")
    assert abs(line.cgst - line.sgst) <= Decimal("0.01")
