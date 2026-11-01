import enum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Role(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    CASHIER = "CASHIER"


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    password_salt: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
