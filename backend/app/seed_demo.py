import argparse
import secrets
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models
from app.config import get_demo_mode, get_demo_username
from app.database import SessionLocal
from app.security import hash_password


DEMO_DATASET_VERSION = 1
DEMO_SEED_ACTION = "demo_seed_completed"
DEMO_SEED_RESOURCE_TYPE = "demo_seed"
BASE_TIMESTAMP = datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc)

SUPPLIER_FIXTURES = (
    {
        "key": "norte",
        "name": "Norte Suprimentos",
        "contact_name": "Equipe Comercial",
        "phone": "+55 11 5555-0101",
        "email": "contato@norte-suprimentos.example.com",
    },
    {
        "key": "orbita",
        "name": "Órbita Tecnologia",
        "contact_name": "Atendimento Corporativo",
        "phone": "+55 11 5555-0102",
        "email": "vendas@orbita-tecnologia.example.com",
    },
    {
        "key": "prisma",
        "name": "Prisma Escritório",
        "contact_name": "Central de Pedidos",
        "phone": "+55 11 5555-0103",
        "email": "pedidos@prisma-escritorio.example.com",
    },
    {
        "key": "atlas",
        "name": "Atlas Mobiliário",
        "contact_name": "Relacionamento B2B",
        "phone": "+55 11 5555-0104",
        "email": "comercial@atlas-mobiliario.example.com",
    },
)

PRODUCT_FIXTURES = (
    {
        "sku": "INF-NBK-001",
        "name": "Notebook Corporativo 14",
        "category": "Informática",
        "minimum_quantity": 10,
        "price": 3899.90,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 40), ("exit", 12)),
    },
    {
        "sku": "INF-MOU-002",
        "name": "Mouse Sem Fio",
        "category": "Informática",
        "minimum_quantity": 20,
        "price": 89.90,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 60), ("exit", 45)),
    },
    {
        "sku": "INF-TEC-003",
        "name": "Teclado USB ABNT2",
        "category": "Informática",
        "minimum_quantity": 8,
        "price": 129.50,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 35), ("exit", 8)),
    },
    {
        "sku": "INF-MON-004",
        "name": "Monitor LED 24",
        "category": "Informática",
        "minimum_quantity": 5,
        "price": 949.00,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 18), ("exit", 10)),
    },
    {
        "sku": "CAB-HDM-005",
        "name": "Cabo HDMI 2 Metros",
        "category": "Cabos e conexões",
        "minimum_quantity": 25,
        "price": 34.90,
        "supplier": "norte",
        "is_active": True,
        "movements": (("entry", 100), ("exit", 72)),
    },
    {
        "sku": "INF-HDS-006",
        "name": "Headset com Microfone",
        "category": "Informática",
        "minimum_quantity": 8,
        "price": 219.90,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 24), ("exit", 19)),
    },
    {
        "sku": "INF-WEB-007",
        "name": "Webcam Full HD",
        "category": "Informática",
        "minimum_quantity": 6,
        "price": 279.00,
        "supplier": "orbita",
        "is_active": True,
        "movements": (("entry", 16), ("exit", 4)),
    },
    {
        "sku": "MOB-CAD-008",
        "name": "Cadeira Ergonômica",
        "category": "Mobiliário",
        "minimum_quantity": 3,
        "price": 1199.00,
        "supplier": "atlas",
        "is_active": True,
        "movements": (("entry", 12), ("exit", 5)),
    },
    {
        "sku": "ESC-PAP-009",
        "name": "Papel A4 Caixa com 10 Resmas",
        "category": "Escritório",
        "minimum_quantity": 15,
        "price": 289.90,
        "supplier": "prisma",
        "is_active": True,
        "movements": (("entry", 50), ("exit", 39)),
    },
    {
        "sku": "IMP-TON-010",
        "name": "Toner Preto Compatível",
        "category": "Impressão",
        "minimum_quantity": 6,
        "price": 189.90,
        "supplier": "prisma",
        "is_active": True,
        "movements": (("entry", 20), ("exit", 15)),
    },
    {
        "sku": "EXP-ETQ-011",
        "name": "Etiqueta Adesiva para Expedição",
        "category": "Expedição",
        "minimum_quantity": 20,
        "price": 74.50,
        "supplier": "norte",
        "is_active": True,
        "movements": (("entry", 80), ("exit", 20)),
    },
    {
        "sku": "EXP-LEI-012",
        "name": "Leitor de Código de Barras USB",
        "category": "Expedição",
        "minimum_quantity": 4,
        "price": 349.00,
        "supplier": "norte",
        "is_active": False,
        "movements": (("entry", 10), ("exit", 3)),
    },
)


class DemoSeedError(RuntimeError):
    pass


@dataclass(frozen=True)
class DemoSeedResult:
    created: bool
    users: int
    suppliers: int
    products: int
    movements: int


def _database_name(db: Session) -> str:
    bind = db.get_bind()
    url = getattr(bind, "url", None)
    if url is None and hasattr(bind, "engine"):
        url = bind.engine.url
    database = url.database if url is not None else None
    if not database:
        raise DemoSeedError("Unable to determine the configured database target")
    return Path(database).name


def _validate_demo_target(db: Session) -> None:
    if not get_demo_mode():
        raise DemoSeedError("Demo seed requires DEMO_MODE=true")

    database_name = _database_name(db)
    if "demo" not in database_name.casefold():
        raise DemoSeedError(
            "Refusing to seed or reset a database whose name does not contain 'demo'"
        )


def _has_seed_marker(db: Session) -> bool:
    return (
        db.query(models.AuditLog)
        .filter(
            models.AuditLog.action == DEMO_SEED_ACTION,
            models.AuditLog.resource_type == DEMO_SEED_RESOURCE_TYPE,
            models.AuditLog.resource_id == DEMO_DATASET_VERSION,
        )
        .first()
        is not None
    )


def _has_application_data(db: Session) -> bool:
    model_types = (
        models.AuditLog,
        models.StockMovement,
        models.Product,
        models.Supplier,
        models.User,
    )
    return any(db.query(model_type).first() is not None for model_type in model_types)


def _delete_application_data(db: Session) -> None:
    for model_type in (
        models.AuditLog,
        models.StockMovement,
        models.Product,
        models.Supplier,
        models.User,
    ):
        db.query(model_type).delete(synchronize_session=False)
    db.flush()


def _calculate_final_quantity(movements: tuple[tuple[str, int], ...]) -> int:
    quantity = 0
    for movement_type, movement_quantity in movements:
        if movement_type == "entry":
            quantity += movement_quantity
        elif movement_type == "exit":
            if movement_quantity > quantity:
                raise DemoSeedError("Demo fixture contains an exit above available stock")
            quantity -= movement_quantity
        else:
            raise DemoSeedError("Demo fixture contains an invalid movement type")
    return quantity


def _create_demo_data(db: Session) -> None:
    demo_user = models.User(
        username=get_demo_username(),
        password_hash=hash_password(secrets.token_urlsafe(48)),
        role=models.UserRole.OPERATOR.value,
        created_at=BASE_TIMESTAMP,
    )
    db.add(demo_user)

    suppliers_by_key = {}
    for index, fixture in enumerate(SUPPLIER_FIXTURES):
        supplier = models.Supplier(
            name=fixture["name"],
            contact_name=fixture["contact_name"],
            phone=fixture["phone"],
            email=fixture["email"],
            created_at=BASE_TIMESTAMP + timedelta(minutes=index),
        )
        db.add(supplier)
        suppliers_by_key[fixture["key"]] = supplier

    db.flush()

    movement_index = 0
    for fixture in PRODUCT_FIXTURES:
        movements = fixture["movements"]
        product = models.Product(
            sku=fixture["sku"],
            name=fixture["name"],
            category=fixture["category"],
            quantity=_calculate_final_quantity(movements),
            minimum_quantity=fixture["minimum_quantity"],
            price=fixture["price"],
            supplier=suppliers_by_key[fixture["supplier"]],
            is_active=fixture["is_active"],
        )
        db.add(product)
        db.flush()

        for movement_type, movement_quantity in movements:
            created_at = BASE_TIMESTAMP + timedelta(hours=movement_index + 1)
            db.add(
                models.StockMovement(
                    product_id=product.id,
                    movement_type=movement_type,
                    quantity=movement_quantity,
                    note="Movimentação fictícia da demonstração",
                    created_at=created_at,
                )
            )
            db.add(
                models.AuditLog(
                    user_id=demo_user.id,
                    action=f"stock_{movement_type}",
                    resource_type="product",
                    resource_id=product.id,
                    created_at=created_at,
                )
            )
            movement_index += 1

    db.add(
        models.AuditLog(
            user_id=demo_user.id,
            action=DEMO_SEED_ACTION,
            resource_type=DEMO_SEED_RESOURCE_TYPE,
            resource_id=DEMO_DATASET_VERSION,
            created_at=BASE_TIMESTAMP + timedelta(days=2),
        )
    )
    db.flush()


def _build_result(db: Session, created: bool) -> DemoSeedResult:
    return DemoSeedResult(
        created=created,
        users=db.query(models.User).count(),
        suppliers=db.query(models.Supplier).count(),
        products=db.query(models.Product).count(),
        movements=db.query(models.StockMovement).count(),
    )


def seed_demo(db: Session | None = None, reset: bool = False) -> DemoSeedResult:
    session = db or SessionLocal()
    owns_session = db is None

    try:
        _validate_demo_target(session)
        with session.begin():
            if _has_seed_marker(session) and not reset:
                return _build_result(session, created=False)

            if reset:
                _delete_application_data(session)
            elif _has_application_data(session):
                raise DemoSeedError(
                    "Demo database contains unmarked data; use --reset explicitly"
                )

            _create_demo_data(session)
            return _build_result(session, created=True)
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara os dados fictícios da demo")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Apaga os dados do banco demo configurado antes de recriar o dataset",
    )
    args = parser.parse_args()

    try:
        result = seed_demo(reset=args.reset)
    except (DemoSeedError, SQLAlchemyError, ValueError) as exc:
        print(f"Falha ao preparar demo: {exc}", file=sys.stderr)
        return 1

    action = "criado" if result.created else "já existente"
    print(
        f"Dataset demo {action}: {result.suppliers} fornecedores, "
        f"{result.products} produtos e {result.movements} movimentações."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
