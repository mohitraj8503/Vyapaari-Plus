from datetime import date

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class BusinessProfile(Base, TimestampMixin):
    __tablename__ = "business_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True, unique=True)
    state_code: Mapped[str] = mapped_column(String(2), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    financial_year_start_month: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    invoice_prefix: Mapped[str] = mapped_column(String(8), default="INV", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def financial_year(self) -> str:
        today = date.today()
        start = today.year if today.month >= self.financial_year_start_month else today.year - 1
        return f"{start}-{str(start + 1)[-2:]}"
