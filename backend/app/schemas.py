from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        return value
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} não pode estar vazio")
    return normalized_value


def normalize_optional_text(value: str | None, field_name: str) -> str | None:
    if value is None or not isinstance(value, str):
        return value
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} não pode conter apenas espaços")
    return normalized_value


def normalize_username(value: str) -> str:
    return normalize_required_text(value, "Username")


def normalize_sku(value: str) -> str:
    if not isinstance(value, str):
        return value
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

    @field_validator("name", "category", mode="before")
    @classmethod
    def normalize_required_product_text(cls, value: str, info) -> str:
        return normalize_required_text(value, info.field_name.capitalize())

    model_config = ConfigDict(extra="forbid")


class ProductCreate(ProductBase):
    sku: str = Field(max_length=64)
    supplier_id: int | None = None

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return normalize_sku(value)


class ProductUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=50)
    minimum_quantity: int = Field(ge=0)
    price: float = Field(ge=0)
    sku: str | None = Field(default=None, max_length=64)
    supplier_id: int | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def normalize_required_product_text(cls, value: str, info) -> str:
        return normalize_required_text(value, info.field_name.capitalize())

    @field_validator("sku", mode="before")
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
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)

    @field_validator("username", mode="before")
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

    @field_validator("username", mode="before")
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

    @field_validator("note", mode="before")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None or not isinstance(value, str):
            return value
        return value.strip()

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

    @field_validator("name", mode="before")
    @classmethod
    def normalize_supplier_name(cls, value: str) -> str:
        return normalize_required_text(value, "Name")

    @field_validator("contact_name", "phone", mode="before")
    @classmethod
    def normalize_optional_supplier_text(cls, value: str | None, info) -> str | None:
        return normalize_optional_text(value, info.field_name.capitalize())

    @field_validator("email", mode="before")
    @classmethod
    def normalize_and_validate_email(cls, value: str | None) -> str | None:
        normalized_email = normalize_optional_text(value, "Email")
        if normalized_email is None:
            return None
        normalized_email = normalized_email.lower()
        if not EMAIL_PATTERN.fullmatch(normalized_email):
            raise ValueError("Email deve ter um formato válido")
        return normalized_email

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
