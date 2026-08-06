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
