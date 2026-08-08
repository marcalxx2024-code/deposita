from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI()


def low_stock_products_query(db: Session):
    return db.query(models.Product).filter(
        models.Product.quantity <= models.Product.minimum_quantity
    )


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


@app.get("/products/low-stock", response_model=list[schemas.ProductResponse])
def list_low_stock_products(db: Session = Depends(get_db)):
    return (
        low_stock_products_query(db)
        .order_by(models.Product.quantity.asc(), models.Product.id.asc())
        .all()
    )


@app.get("/dashboard/summary", response_model=schemas.DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    total_products = db.query(models.Product).count()
    total_stock_quantity = db.query(
        func.coalesce(func.sum(models.Product.quantity), 0)
    ).scalar()
    low_stock_products = low_stock_products_query(db).count()
    recent_movements = (
        db.query(models.StockMovement)
        .order_by(models.StockMovement.created_at.desc(), models.StockMovement.id.desc())
        .limit(5)
        .all()
    )

    return {
        "total_products": total_products,
        "total_stock_quantity": total_stock_quantity,
        "low_stock_products": low_stock_products,
        "recent_movements": recent_movements,
    }


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


@app.post(
    "/products/{product_id}/movements/entry",
    response_model=schemas.StockMovementResponse,
    status_code=201,
)
def create_stock_entry(
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    db: Session = Depends(get_db),
):
    if movement_data.movement_type != "entry":
        raise HTTPException(
            status_code=400,
            detail="Tipo de movimentação inválido para esta rota",
        )

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    product.quantity += movement_data.quantity
    movement = models.StockMovement(
        product_id=product_id,
        movement_type="entry",
        quantity=movement_data.quantity,
        note=movement_data.note,
    )
    db.add(movement)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(movement)
    return movement


@app.post(
    "/products/{product_id}/movements/exit",
    response_model=schemas.StockMovementResponse,
    status_code=201,
)
def create_stock_exit(
    product_id: int,
    movement_data: schemas.StockMovementCreate,
    db: Session = Depends(get_db),
):
    if movement_data.movement_type != "exit":
        raise HTTPException(
            status_code=400,
            detail="Tipo de movimentação inválido para esta rota",
        )

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if movement_data.quantity > product.quantity:
        raise HTTPException(status_code=400, detail="Estoque insuficiente")

    product.quantity -= movement_data.quantity
    movement = models.StockMovement(
        product_id=product_id,
        movement_type="exit",
        quantity=movement_data.quantity,
        note=movement_data.note,
    )
    db.add(movement)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    db.refresh(movement)
    return movement


@app.get("/movements", response_model=list[schemas.StockMovementResponse])
def list_stock_movements(db: Session = Depends(get_db)):
    return (
        db.query(models.StockMovement)
        .order_by(models.StockMovement.created_at.desc(), models.StockMovement.id.desc())
        .all()
    )
