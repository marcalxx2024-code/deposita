import logging

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.database import Base, engine, get_db, normalize_search_text
from app.errors import (
    APIError,
    invalid_authentication_error,
    invalid_credentials_error,
    product_not_found_error,
    username_already_exists_error,
)
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    validate_auth_settings,
    verify_password,
)

validate_auth_settings()
Base.metadata.create_all(bind=engine)

app = FastAPI()
logger = logging.getLogger(__name__)
DUMMY_PASSWORD_HASH = hash_password("not-a-valid-user-password")


def error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None, **extra
):
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, **extra}},
        headers=headers,
    )


@app.exception_handler(APIError)
async def api_error_handler(_request: Request, exc: APIError):
    return error_response(exc.status_code, exc.code, exc.message, exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError):
    details = [
        {
            "field": ".".join(str(location) for location in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    return error_response(
        422,
        "VALIDATION_ERROR",
        "Dados de entrada inválidos",
        details=details,
    )


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_request: Request, exc: SQLAlchemyError):
    logger.exception("Database error while processing request", exc_info=exc)
    return error_response(500, "DATABASE_ERROR", "Erro interno ao processar dados")


@app.exception_handler(Exception)
async def internal_error_handler(_request: Request, exc: Exception):
    logger.exception("Unexpected error while processing request", exc_info=exc)
    return error_response(500, "INTERNAL_SERVER_ERROR", "Erro interno do servidor")


def filter_by_low_stock(query, low_stock: bool):
    if low_stock:
        return query.filter(models.Product.quantity <= models.Product.minimum_quantity)

    return query.filter(models.Product.quantity > models.Product.minimum_quantity)


def low_stock_products_query(db: Session):
    return filter_by_low_stock(db.query(models.Product), low_stock=True)


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


@app.post("/users", response_model=schemas.UserResponse, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(
        username=user.username,
        password_hash=hash_password(user.password),
    )
    db.add(db_user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise username_already_exists_error()

    db.refresh(db_user)
    return db_user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    if authorization is None:
        raise invalid_authentication_error()

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise invalid_authentication_error()

    try:
        user_id = int(decode_access_token(token))
    except (InvalidTokenError, ValueError):
        raise invalid_authentication_error()

    user = db.get(models.User, user_id)
    if user is None:
        raise invalid_authentication_error()
    return user


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(models.User)
        .filter(models.User.username == credentials.username)
        .first()
    )
    password_to_verify = user.password_hash if user is not None else DUMMY_PASSWORD_HASH

    if not verify_password(credentials.password, password_to_verify) or user is None:
        raise invalid_credentials_error()

    return {
        "access_token": create_access_token(str(user.id)),
        "token_type": "bearer",
    }


@app.get("/auth/me", response_model=schemas.UserResponse)
def get_authenticated_user(current_user: models.User = Depends(get_current_user)):
    return current_user


@app.get("/products", response_model=schemas.PaginatedProductResponse)
def list_products(
    search: str | None = None,
    low_stock: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(models.Product)

    if search is not None:
        normalized_search = normalize_search_text(search)
        query = query.filter(
            func.normalize_search_text(models.Product.name).like(
                f"%{normalized_search}%"
            )
        )

    if low_stock is not None:
        query = filter_by_low_stock(query, low_stock)

    total = query.count()
    products = (
        query.order_by(models.Product.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": products,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


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
        raise product_not_found_error()
    return product


@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise product_not_found_error()

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
        raise product_not_found_error()

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
        raise APIError(
            status_code=400,
            code="INVALID_MOVEMENT_TYPE",
            message="Tipo de movimentação inválido para esta rota",
        )

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise product_not_found_error()

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
        raise APIError(
            status_code=400,
            code="INVALID_MOVEMENT_TYPE",
            message="Tipo de movimentação inválido para esta rota",
        )

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise product_not_found_error()

    if movement_data.quantity > product.quantity:
        raise APIError(
            status_code=409,
            code="INSUFFICIENT_STOCK",
            message="Estoque insuficiente",
        )

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
