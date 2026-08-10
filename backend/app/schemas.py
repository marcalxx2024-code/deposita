from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_username(value: str) -> str:
    normalized_username = value.strip()
    if not normalized_username:
        raise ValueError("Username não pode estar vazio")
    return normalized_username


def normalize_sku(value: str) -> str:
    normalized_sku = value.strip().upper()
    if not normalized_sku:
        raise ValueError("SKU nÃ£o pode estar vazio")
    return normalized_sku


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    quantity: int = Field(ge=0)
    minimum_quantity: int = Field(ge=0)
    price: float = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class ProductCreate(ProductBase):
    sku: str
    supplier_id: int | None = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return normalize_sku(value)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    minimum_quantity: int = Field(ge=0)
    price: float = Field(ge=0)
    sku: str | None = None
    supplier_id: int | None = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_sku(value)

    @model_validator(mode="after")
    def reject_null_sku(self):
        if "sku" in self.model_fields_set and self.sku is None:
            raise ValueError("SKU nÃ£o pode estar vazio")
        return self

    model_config = ConfigDict(extra="forbid")


class ProductResponse(ProductBase):
    id: int
    sku: str
    supplier_id: int | None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return normalize_username(value)

    model_config = ConfigDict(extra="forbid")


class UserResponse(BaseModel):
    id: int
    username: str
    role: Literal["admin", "operator"]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return normalize_username(value)

    model_config = ConfigDict(extra="forbid")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


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


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    resource_type: str
    resource_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SupplierBase(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    contact_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)

    model_config = ConfigDict(extra="forbid")


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    total_products: int
    total_stock_quantity: int
    low_stock_products: int
    recent_movements: list[StockMovementResponse]

    model_config = ConfigDict(extra="forbid", from_attributes=True)
