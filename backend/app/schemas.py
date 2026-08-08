from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)
    price: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    minimum_quantity: int = Field(ge=0)
    price: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ProductResponse(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class PaginatedProductResponse(BaseModel):
    items: list[ProductResponse]
    page: int
    page_size: int
    total: int
    pages: int

    model_config = ConfigDict(extra="forbid")


class StockMovementCreate(BaseModel):
    movement_type: Literal["entry", "exit"]
    quantity: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class StockMovementResponse(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: int
    note: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    total_products: int
    total_stock_quantity: int
    low_stock_products: int
    recent_movements: list[StockMovementResponse]

    model_config = ConfigDict(extra="forbid", from_attributes=True)
