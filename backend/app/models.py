from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from app.database import Base


class UTCDateTime(TypeDecorator):
    """Store UTC datetimes in SQLite and return them as timezone-aware values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    contact_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)

    products = relationship(
        "Product",
        back_populates="supplier",
        passive_deletes=True,
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    minimum_quantity = Column(Integer, nullable=False, default=0)
    price = Column(Float, nullable=False, default=0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True, index=True)
    sku = Column(String, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")

    supplier = relationship("Supplier", back_populates="products")

    movements = relationship(
        "StockMovement",
        back_populates="product",
        passive_deletes=True,
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)

    product = relationship("Product", back_populates="movements")


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'operator')", name="valid_user_role"),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default=UserRole.OPERATOR.value)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now)

    audit_logs = relationship(
        "AuditLog",
        back_populates="user",
        passive_deletes=True,
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(Integer, nullable=False)
    created_at = Column(UTCDateTime(), nullable=False, default=utc_now, index=True)

    user = relationship("User", back_populates="audit_logs")
