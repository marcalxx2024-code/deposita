from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    name: str
    category: str
    quantity: int
    minimum_quantity: int
    price: float


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int

    model_config = ConfigDict(from_attributes=True)