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


def test_list_low_stock_products_returns_only_low_stock_in_quantity_order():
    with TestClient(app) as client:
        above_minimum = client.post(
            "/products",
            json={
                "name": "Estoque acima",
                "category": "Teste",
                "quantity": 6,
                "minimum_quantity": 5,
                "price": 10.0,
            },
        )
        equal_to_minimum = client.post(
            "/products",
            json={
                "name": "Estoque mínimo",
                "category": "Teste",
                "quantity": 3,
                "minimum_quantity": 3,
                "price": 10.0,
            },
        )
        below_minimum = client.post(
            "/products",
            json={
                "name": "Estoque baixo",
                "category": "Teste",
                "quantity": 1,
                "minimum_quantity": 2,
                "price": 10.0,
            },
        )
        response = client.get("/products/low-stock")

    assert above_minimum.status_code == 200
    assert equal_to_minimum.status_code == 200
    assert below_minimum.status_code == 200
    assert response.status_code == 200

    products = response.json()
    assert [product["id"] for product in products] == [
        below_minimum.json()["id"],
        equal_to_minimum.json()["id"],
    ]
    assert [product["quantity"] for product in products] == [1, 3]


def test_dashboard_summary_returns_zeros_for_empty_database():
    with TestClient(app) as client:
        response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_products": 0,
        "total_stock_quantity": 0,
        "low_stock_products": 0,
        "recent_movements": [],
    }


def test_dashboard_summary_calculates_inventory_indicators():
    products = [
        {
            "name": "Estoque normal",
            "category": "Teste",
            "quantity": 10,
            "minimum_quantity": 3,
            "price": 2.5,
        },
        {
            "name": "Estoque baixo",
            "category": "Teste",
            "quantity": 2,
            "minimum_quantity": 2,
            "price": 3.25,
        },
        {
            "name": "Estoque zerado",
            "category": "Teste",
            "quantity": 0,
            "minimum_quantity": 1,
            "price": 7.0,
        },
    ]

    with TestClient(app) as client:
        for product in products:
            create_response = client.post("/products", json=product)
            assert create_response.status_code == 200

        response = client.get("/dashboard/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_products": 3,
        "total_stock_quantity": 12,
        "low_stock_products": 2,
        "recent_movements": [],
    }


def test_dashboard_summary_returns_five_most_recent_movements():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)
        movement_responses = []

        for quantity in range(1, 7):
            response = client.post(
                f"/products/{product['id']}/movements/entry",
                json={"movement_type": "entry", "quantity": quantity},
            )
            assert response.status_code == 201
            movement_responses.append(response.json())

        summary_response = client.get("/dashboard/summary")

    assert summary_response.status_code == 200
    recent_movements = summary_response.json()["recent_movements"]
    assert len(recent_movements) == 5
    assert [movement["id"] for movement in recent_movements] == [
        movement["id"] for movement in reversed(movement_responses[-5:])
    ]
