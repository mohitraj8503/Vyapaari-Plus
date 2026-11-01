import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class CustomerEntryType(str, enum.Enum):
    SALE = "SALE"
    PAYMENT = "PAYMENT"
    REVERSAL = "REVERSAL"


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class CustomerLedgerEntry(Base, TimestampMixin):
    __tablename__ = "customer_ledger_entries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    entry_type: Mapped[CustomerEntryType] = mapped_column(Enum(CustomerEntryType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    @property
    def signed_amount(self) -> Decimal:
        return -self.amount if self.entry_type in (CustomerEntryType.PAYMENT, CustomerEntryType.REVERSAL) else self.amount
