from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/health")
def health_check():
    return {"status": "online"}


@app.post("/products", response_model=schemas.ProductResponse)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.get("/products", response_model=list[schemas.ProductResponse])
def list_products(db: Session = Depends(get_db)):
    return db.query(models.Product).order_by(models.Product.id.asc()).all()


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    return product


@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product.name = product_data.name
    product.category = product_data.category
    product.minimum_quantity = product_data.minimum_quantity
    product.price = product_data.price

    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=200)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    db.delete(product)
    db.commit()
    return {"message": "Produto excluído com sucesso"}
