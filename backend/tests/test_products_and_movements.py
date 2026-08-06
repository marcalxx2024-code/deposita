from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


TEST_DATABASE_URL = "sqlite:///./test_deposita.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_function():
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_product(client: TestClient, quantity: int) -> dict:
    response = client.post(
        "/products",
        json={
            "name": "Produto de teste",
            "category": "Teste",
            "quantity": quantity,
            "minimum_quantity": 2,
            "price": 10.5,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_product_returns_id():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

    assert isinstance(product["id"], int)


def test_create_stock_entry_updates_product_quantity():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 5, "note": "Reposição"},
        )

        assert response.status_code == 201
        assert response.json()["movement_type"] == "entry"

        product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["quantity"] == 15


def test_create_stock_exit_updates_product_quantity():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 4, "note": "Venda"},
        )

        assert response.status_code == 201
        assert response.json()["movement_type"] == "exit"

        product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["quantity"] == 6


def test_stock_exit_larger_than_available_stock_is_rejected():
    with TestClient(app) as client:
        product = create_product(client, quantity=3)

        response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 5},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Estoque insuficiente"

        product_response = client.get(f"/products/{product['id']}")

    assert product_response.status_code == 200
    assert product_response.json()["quantity"] == 3


def test_movement_for_nonexistent_product_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/products/999/movements/entry",
            json={"movement_type": "entry", "quantity": 1},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Produto não encontrado"


def test_incorrect_movement_type_for_route_is_rejected():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "entry", "quantity": 1},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Tipo de movimentação inválido para esta rota"


def test_list_stock_movements_returns_most_recent_first():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        entry_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 5},
        )
        exit_response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 4},
        )
        movements_response = client.get("/movements")

    assert entry_response.status_code == 201
    assert exit_response.status_code == 201
    assert movements_response.status_code == 200

    movements = movements_response.json()
    assert len(movements) == 2
    assert movements[0]["id"] == exit_response.json()["id"]
    assert movements[0]["movement_type"] == "exit"
    assert movements[1]["id"] == entry_response.json()["id"]
    assert movements[1]["movement_type"] == "entry"
