import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.security import hash_password
from app.seed_demo import (
    PRODUCT_FIXTURES,
    SUPPLIER_FIXTURES,
    DemoSeedError,
    seed_demo,
)


@pytest.fixture
def demo_session_factory(tmp_path, monkeypatch):
    database_path = tmp_path / "deposita_demo_test.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_USERNAME", "demo-test")

    try:
        yield session_factory
    finally:
        engine.dispose()


def run_seed(session_factory, reset=False):
    with session_factory() as db:
        return seed_demo(db=db, reset=reset)


def test_seed_is_refused_when_demo_mode_is_disabled(
    demo_session_factory, monkeypatch
):
    monkeypatch.setenv("DEMO_MODE", "false")

    with pytest.raises(DemoSeedError, match="DEMO_MODE=true"):
        run_seed(demo_session_factory)

    with demo_session_factory() as db:
        assert db.query(models.User).count() == 0
        assert db.query(models.Product).count() == 0


def test_seed_creates_only_the_configured_demo_operator(demo_session_factory):
    result = run_seed(demo_session_factory)

    with demo_session_factory() as db:
        users = db.query(models.User).all()

    assert result.created is True
    assert len(users) == 1
    assert users[0].username == "demo-test"
    assert users[0].role == models.UserRole.OPERATOR.value
    assert users[0].password_hash
    assert "demo-test" not in users[0].password_hash
    assert all(user.role != models.UserRole.ADMIN.value for user in users)


def test_seed_creates_expected_fictitious_suppliers(demo_session_factory):
    run_seed(demo_session_factory)

    with demo_session_factory() as db:
        suppliers = db.query(models.Supplier).order_by(models.Supplier.name).all()

    assert len(suppliers) == len(SUPPLIER_FIXTURES) == 4
    assert {supplier.name for supplier in suppliers} == {
        fixture["name"] for fixture in SUPPLIER_FIXTURES
    }
    assert all(
        supplier.email is None or supplier.email.endswith("example.com")
        for supplier in suppliers
    )


def test_seed_creates_varied_products_with_unique_skus(demo_session_factory):
    run_seed(demo_session_factory)

    with demo_session_factory() as db:
        products = db.query(models.Product).all()

    skus = [product.sku for product in products]
    assert len(products) == len(PRODUCT_FIXTURES) == 12
    assert len(skus) == len(set(skus))
    assert len({product.category for product in products}) >= 4
    assert any(product.quantity <= product.minimum_quantity for product in products)
    assert any(not product.is_active for product in products)
    assert all(product.price > 0 for product in products)


def test_seed_creates_entries_exits_and_audit_logs(demo_session_factory):
    result = run_seed(demo_session_factory)

    with demo_session_factory() as db:
        movements = db.query(models.StockMovement).all()
        movement_audits = (
            db.query(models.AuditLog)
            .filter(models.AuditLog.resource_type == "product")
            .all()
        )

    assert result.movements == 24
    assert 15 <= len(movements) <= 25
    assert {movement.movement_type for movement in movements} == {"entry", "exit"}
    assert len(movement_audits) == len(movements)


def test_seed_product_quantities_match_complete_movement_history(
    demo_session_factory,
):
    run_seed(demo_session_factory)

    with demo_session_factory() as db:
        products = db.query(models.Product).all()
        movements = db.query(models.StockMovement).all()

    net_quantities = {product.id: 0 for product in products}
    for movement in movements:
        direction = 1 if movement.movement_type == "entry" else -1
        net_quantities[movement.product_id] += direction * movement.quantity

    assert all(
        product.quantity == net_quantities[product.id] for product in products
    )
    assert all(product.quantity >= 0 for product in products)


def test_repeated_seed_does_not_duplicate_records(demo_session_factory):
    first_result = run_seed(demo_session_factory)
    second_result = run_seed(demo_session_factory)

    with demo_session_factory() as db:
        counts = {
            "users": db.query(models.User).count(),
            "suppliers": db.query(models.Supplier).count(),
            "products": db.query(models.Product).count(),
            "movements": db.query(models.StockMovement).count(),
        }

    assert first_result.created is True
    assert second_result.created is False
    assert counts == {
        "users": 1,
        "suppliers": 4,
        "products": 12,
        "movements": 24,
    }


def test_seed_refuses_partial_unmarked_demo_data_without_reset(
    demo_session_factory,
):
    with demo_session_factory() as db:
        db.add(
            models.Supplier(
                name="Dado parcial",
                email="parcial@example.com",
            )
        )
        db.commit()

    with pytest.raises(DemoSeedError, match="unmarked data"):
        run_seed(demo_session_factory)

    with demo_session_factory() as db:
        assert db.query(models.Supplier).count() == 1
        assert db.query(models.Product).count() == 0


def test_explicit_reset_recreates_the_expected_dataset(demo_session_factory):
    run_seed(demo_session_factory)

    with demo_session_factory() as db:
        product = db.query(models.Product).filter_by(sku="INF-NBK-001").one()
        product.quantity = 999
        db.add(
            models.User(
                username="temporary-admin",
                password_hash=hash_password("temporary-password"),
                role=models.UserRole.ADMIN.value,
            )
        )
        db.commit()

    reset_result = run_seed(demo_session_factory, reset=True)

    with demo_session_factory() as db:
        product = db.query(models.Product).filter_by(sku="INF-NBK-001").one()
        users = db.query(models.User).all()

    assert reset_result.created is True
    assert product.quantity == 28
    assert [(user.username, user.role) for user in users] == [
        ("demo-test", models.UserRole.OPERATOR.value)
    ]


def test_normal_database_target_is_not_modified(tmp_path, monkeypatch):
    database_path = tmp_path / "deposita_test.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("DEMO_USERNAME", "demo-test")

    try:
        with session_factory() as db:
            db.add(
                models.User(
                    username="normal-user",
                    password_hash=hash_password("normal-password"),
                    role=models.UserRole.OPERATOR.value,
                )
            )
            db.commit()

        with session_factory() as db:
            with pytest.raises(DemoSeedError, match="does not contain 'demo'"):
                seed_demo(db=db, reset=True)

        with session_factory() as db:
            assert [user.username for user in db.query(models.User).all()] == [
                "normal-user"
            ]
            assert db.query(models.Supplier).count() == 0
            assert db.query(models.Product).count() == 0
    finally:
        engine.dispose()
