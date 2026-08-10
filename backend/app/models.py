from datetime import datetime
from enum import Enum

from sqlalchemy import CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    minimum_quantity = Column(Integer, nullable=False, default=0)
    price = Column(Float, nullable=False, default=0)

    movements = relationship(
        "StockMovement",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
