from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String
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
