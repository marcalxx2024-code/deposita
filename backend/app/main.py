import logging

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from jwt import InvalidTokenError
from sqlalchemy import func, inspect
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.database import engine, get_db, normalize_search_text
from app.errors import (
    APIError,
    forbidden_error,
    invalid_authentication_error,
    invalid_credentials_error,
    product_not_found_error,
    supplier_in_use_error,
    supplier_not_found_error,
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


def validate_user_role_column() -> None:
    user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "role" not in user_columns:
        raise RuntimeError(
            "The users table is missing the role column. Update the SQLite database "
            "manually before starting the application."
        )


validate_user_role_column()

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


def get_supplier_or_error(supplier_id: int, db: Session) -> models.Supplier:
    supplier = db.get(models.Supplier, supplier_id)
    if supplier is None:
        raise supplier_not_found_error()
    return supplier


@app.get("/health")
def health_check():
    return {"status": "online"}


@app.post("/users", response_model=schemas.UserResponse, status_code=201)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(
        username=user.username,
        password_hash=hash_password(user.password),
        role=models.UserRole.OPERATOR.value,
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


def require_roles(*allowed_roles: models.UserRole):
    allowed_role_values = {role.value for role in allowed_roles}

    def role_dependency(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        if current_user.role not in allowed_role_values:
            raise forbidden_error()
        return current_user

    return role_dependency


require_admin = require_roles(models.UserRole.ADMIN)
require_inventory_write = require_roles(
    models.UserRole.ADMIN,
    models.UserRole.OPERATOR,
)


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


@app.post("/products", response_model=schemas.ProductResponse)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    if product.supplier_id is not None:
        get_supplier_or_error(product.supplier_id, db)

    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.flush()
    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="product_created",
            resource_type="product",
            resource_id=db_product.id,
        )
    )
    db.commit()
    db.refresh(db_product)
    return db_product


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
    current_user: models.User = Depends(require_admin),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise product_not_found_error()

    product.name = product_data.name
    product.category = product_data.category
    product.minimum_quantity = product_data.minimum_quantity
    product.price = product_data.price
    if "supplier_id" in product_data.model_fields_set:
        if product_data.supplier_id is not None:
            get_supplier_or_error(product_data.supplier_id, db)
        product.supplier_id = product_data.supplier_id

    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="product_updated",
            resource_type="product",
            resource_id=product.id,
        )
    )
    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", status_code=200)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if product is None:
        raise product_not_found_error()

    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="product_deleted",
            resource_type="product",
            resource_id=product.id,
        )
    )
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
    current_user: models.User = Depends(require_inventory_write),
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
    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="stock_entry",
            resource_type="product",
            resource_id=product.id,
        )
    )

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
    current_user: models.User = Depends(require_inventory_write),
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
    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="stock_exit",
            resource_type="product",
            resource_id=product.id,
        )
    )

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


@app.get("/audit-logs", response_model=list[schemas.AuditLogResponse])
def list_audit_logs(
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_admin),
):
    return (
        db.query(models.AuditLog)
        .order_by(models.AuditLog.created_at.desc(), models.AuditLog.id.desc())
        .all()
    )


@app.post("/suppliers", response_model=schemas.SupplierResponse, status_code=201)
def create_supplier(
    supplier: schemas.SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.flush()
    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="supplier_created",
            resource_type="supplier",
            resource_id=db_supplier.id,
        )
    )
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@app.get("/suppliers", response_model=list[schemas.SupplierResponse])
def list_suppliers(
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_user),
):
    return db.query(models.Supplier).order_by(models.Supplier.id.asc()).all()


@app.get("/suppliers/{supplier_id}", response_model=schemas.SupplierResponse)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_user),
):
    return get_supplier_or_error(supplier_id, db)


@app.put("/suppliers/{supplier_id}", response_model=schemas.SupplierResponse)
def update_supplier(
    supplier_id: int,
    supplier_data: schemas.SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    supplier = get_supplier_or_error(supplier_id, db)
    for field, value in supplier_data.model_dump().items():
        setattr(supplier, field, value)
    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="supplier_updated",
            resource_type="supplier",
            resource_id=supplier.id,
        )
    )
    db.commit()
    db.refresh(supplier)
    return supplier


@app.delete("/suppliers/{supplier_id}", status_code=200)
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_admin),
):
    supplier = get_supplier_or_error(supplier_id, db)
    if db.query(models.Product).filter(models.Product.supplier_id == supplier.id).first():
        raise supplier_in_use_error()

    db.add(
        models.AuditLog(
            user_id=current_user.id,
            action="supplier_deleted",
            resource_type="supplier",
            resource_id=supplier.id,
        )
    )
    db.delete(supplier)
    db.commit()
    return {"message": "Fornecedor excluÃ­do com sucesso"}
