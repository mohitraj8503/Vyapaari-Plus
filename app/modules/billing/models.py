import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin


class PaymentMode(str, enum.Enum):
    CASH = "CASH"
    CARD = "CARD"
    UPI = "UPI"
    UDHAAR = "UDHAAR"


class InvoiceCounter(Base):
    __tablename__ = "invoice_counters"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SalesInvoice(Base, TimestampMixin):
    __tablename__ = "sales_invoices"
    __table_args__ = (UniqueConstraint("business_id", "financial_year", "invoice_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    business_id: Mapped[str] = mapped_column(ForeignKey("business_profiles.id"), nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(16), nullable=False)
    financial_year: Mapped[str] = mapped_column(String(7), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    place_of_supply: Mapped[str] = mapped_column(String(2), nullable=False)
    taxable_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    round_off: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lines: Mapped[list["SalesInvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    payments: Mapped[list["SalesPayment"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class SalesInvoiceLine(Base):
    __tablename__ = "sales_invoice_lines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    invoice: Mapped["SalesInvoice"] = relationship(back_populates="lines")


class SalesPayment(Base):
    __tablename__ = "sales_payments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[PaymentMode] = mapped_column(Enum(PaymentMode), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    invoice: Mapped["SalesInvoice"] = relationship(back_populates="payments")
