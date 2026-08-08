import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.security import create_access_token, verify_password


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


def create_product(
    client: TestClient,
    quantity: int,
    name: str = "Produto de teste",
    minimum_quantity: int = 2,
) -> dict:
    response = client.post(
        "/products",
        json={
            "name": name,
            "category": "Teste",
            "quantity": quantity,
            "minimum_quantity": minimum_quantity,
            "price": 10.5,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_create_product_returns_id():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

    assert isinstance(product["id"], int)


def test_create_user_hashes_password_and_hides_sensitive_fields():
    plain_password = "uma-senha-segura"

    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={"username": "guilherme", "password": plain_password},
        )

    assert response.status_code == 201
    user_response = response.json()
    assert user_response["username"] == "guilherme"
    assert "id" in user_response
    assert "created_at" in user_response
    assert "password" not in user_response
    assert "password_hash" not in user_response

    db = TestingSessionLocal()
    try:
        stored_user = db.query(User).filter(User.id == user_response["id"]).one()
    finally:
        db.close()

    assert stored_user.password_hash != plain_password
    assert verify_password(plain_password, stored_user.password_hash)
    assert not verify_password("senha-incorreta", stored_user.password_hash)


def test_create_user_rejects_duplicate_username():
    with TestClient(app) as client:
        first_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        duplicate_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "outra-senha-segura"},
        )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "USERNAME_ALREADY_EXISTS"


def test_create_user_validates_password_length_and_username():
    with TestClient(app) as client:
        short_password_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "curta"},
        )
        empty_username_response = client.post(
            "/users",
            json={"username": "", "password": "uma-senha-segura"},
        )
        whitespace_username_response = client.post(
            "/users",
            json={"username": "   ", "password": "uma-senha-segura"},
        )

    for response in (
        short_password_response,
        empty_username_response,
        whitespace_username_response,
    ):
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_returns_bearer_access_token_for_valid_credentials():
    with TestClient(app) as client:
        create_user_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        response = client.post(
            "/auth/login",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )

    assert create_user_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["token_type"] == "bearer"


def test_login_returns_same_error_for_invalid_credentials():
    with TestClient(app) as client:
        create_user_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        wrong_password_response = client.post(
            "/auth/login",
            json={"username": "guilherme", "password": "senha-incorreta"},
        )
        unknown_user_response = client.post(
            "/auth/login",
            json={"username": "inexistente", "password": "senha-incorreta"},
        )

    assert create_user_response.status_code == 201
    for response in (wrong_password_response, unknown_user_response):
        assert response.status_code == 401
        assert response.json()["error"] == {
            "code": "INVALID_CREDENTIALS",
            "message": "Credenciais inválidas",
        }


def test_auth_me_requires_a_valid_token_and_hides_password_hash():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        login_response = client.post(
            "/auth/login",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        missing_token_response = client.get("/auth/me")
        authenticated_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        )

    assert user_response.status_code == 201
    assert missing_token_response.status_code == 401
    assert missing_token_response.json()["error"]["code"] == "INVALID_AUTHENTICATION"
    assert missing_token_response.headers["www-authenticate"] == "Bearer"
    assert authenticated_response.status_code == 200
    assert authenticated_response.json()["id"] == user_response.json()["id"]
    assert authenticated_response.json()["username"] == "guilherme"
    assert "password_hash" not in authenticated_response.json()


def test_auth_me_rejects_tampered_expired_and_unexpected_algorithm_tokens():
    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={"username": "guilherme", "password": "uma-senha-segura"},
        )
        user_id = user_response.json()["id"]
        expired_token = create_access_token(
            str(user_id), expires_delta=timedelta(seconds=-1)
        )
        unexpected_algorithm_token = jwt.encode(
            {
                "sub": str(user_id),
                "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
            },
            os.environ["DEPOSITA_SECRET_KEY"],
            algorithm="HS384",
        )

        tampered_response = client.get(
            "/auth/me", headers={"Authorization": "Bearer tampered-token"}
        )
        expired_response = client.get(
            "/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
        )
        unexpected_algorithm_response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {unexpected_algorithm_token}"},
        )

    assert user_response.status_code == 201
    for response in (
        tampered_response,
        expired_response,
        unexpected_algorithm_response,
    ):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_AUTHENTICATION"


def test_product_not_found_errors_are_standardized():
    product_data = {
        "name": "Produto válido",
        "category": "Teste",
        "minimum_quantity": 2,
        "price": 10.5,
    }

    with TestClient(app) as client:
        get_response = client.get("/products/999")
        update_response = client.put("/products/999", json=product_data)
        delete_response = client.delete("/products/999")

    for response in (get_response, update_response, delete_response):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
        assert response.json()["error"]["message"] == "Produto não encontrado"


def test_invalid_payload_returns_safe_validation_details():
    with TestClient(app) as client:
        response = client.post(
            "/products",
            json={
                "name": "A",
                "category": "",
                "quantity": -1,
                "minimum_quantity": -1,
                "price": -1,
            },
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"] == "Dados de entrada inválidos"
    assert {detail["field"] for detail in error["details"]} == {
        "body.name",
        "body.category",
        "body.quantity",
        "body.minimum_quantity",
        "body.price",
    }
    assert all("input" not in detail for detail in error["details"])


def test_list_products_uses_default_pagination():
    with TestClient(app) as client:
        for index in range(21):
            create_product(client, quantity=index, name=f"Produto {index}")

        response = client.get("/products")

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] == 21
    assert data["pages"] == 2
    assert [product["id"] for product in data["items"]] == list(range(1, 21))


def test_list_products_supports_custom_page_and_page_size():
    with TestClient(app) as client:
        for index in range(5):
            create_product(client, quantity=index, name=f"Produto {index}")

        response = client.get("/products", params={"page": 2, "page_size": 2})

    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert data["total"] == 5
    assert data["pages"] == 3
    assert [product["id"] for product in data["items"]] == [3, 4]


def test_list_products_searches_name_case_insensitively():
    with TestClient(app) as client:
        matching_product = create_product(
            client, quantity=5, name="Teclado Mecanico"
        )
        create_product(client, quantity=5, name="Mouse")

        response = client.get("/products", params={"search": "MECANICO"})

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [product["id"] for product in data["items"]] == [matching_product["id"]]


def test_list_products_searches_names_without_accents():
    with TestClient(app) as client:
        coffee = create_product(client, quantity=5, name="Café especial")
        sugar = create_product(client, quantity=5, name="Açúcar mascavo")
        soap = create_product(client, quantity=5, name="Sabão em pó")

        coffee_response = client.get("/products", params={"search": "cafe"})
        sugar_response = client.get("/products", params={"search": "acucar"})
        soap_response = client.get("/products", params={"search": "sabao"})
        upper_case_response = client.get("/products", params={"search": "CAFE"})
        partial_response = client.get("/products", params={"search": "acu"})

    assert [product["id"] for product in coffee_response.json()["items"]] == [
        coffee["id"]
    ]
    assert [product["id"] for product in sugar_response.json()["items"]] == [
        sugar["id"]
    ]
    assert [product["id"] for product in soap_response.json()["items"]] == [soap["id"]]
    assert [product["id"] for product in upper_case_response.json()["items"]] == [
        coffee["id"]
    ]
    assert [product["id"] for product in partial_response.json()["items"]] == [
        sugar["id"]
    ]


def test_list_products_combines_accent_insensitive_search_with_pagination():
    with TestClient(app) as client:
        create_product(client, quantity=5, name="Café primeiro")
        second_coffee = create_product(client, quantity=5, name="Café segundo")
        create_product(client, quantity=5, name="Café terceiro")

        response = client.get(
            "/products", params={"search": "cafe", "page": 2, "page_size": 1}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["pages"] == 3
    assert [product["id"] for product in data["items"]] == [second_coffee["id"]]


def test_list_products_combines_accent_insensitive_search_with_low_stock():
    with TestClient(app) as client:
        low_stock_coffee = create_product(
            client, quantity=1, minimum_quantity=2, name="Café baixo"
        )
        create_product(client, quantity=3, minimum_quantity=2, name="Café normal")

        response = client.get(
            "/products", params={"search": "cafe", "low_stock": True}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert [product["id"] for product in data["items"]] == [low_stock_coffee["id"]]


def test_list_products_filters_low_stock_and_combines_filters_with_pagination():
    with TestClient(app) as client:
        low_stock_first = create_product(
            client, quantity=1, minimum_quantity=2, name="Baixo primeiro"
        )
        low_stock_second = create_product(
            client, quantity=2, minimum_quantity=2, name="Baixo segundo"
        )
        normal_stock = create_product(
            client, quantity=3, minimum_quantity=2, name="Estoque normal"
        )

        low_stock_response = client.get("/products", params={"low_stock": True})
        normal_stock_response = client.get("/products", params={"low_stock": False})
        combined_response = client.get(
            "/products",
            params={"search": "baixo", "low_stock": True, "page": 2, "page_size": 1},
        )

    assert low_stock_response.status_code == 200
    assert [product["id"] for product in low_stock_response.json()["items"]] == [
        low_stock_first["id"],
        low_stock_second["id"],
    ]
    assert normal_stock_response.status_code == 200
    assert [product["id"] for product in normal_stock_response.json()["items"]] == [
        normal_stock["id"]
    ]
    assert combined_response.status_code == 200
    combined_data = combined_response.json()
    assert combined_data["total"] == 2
    assert combined_data["pages"] == 2
    assert [product["id"] for product in combined_data["items"]] == [
        low_stock_second["id"]
    ]


def test_list_products_rejects_invalid_pagination_values():
    with TestClient(app) as client:
        oversized_response = client.get("/products", params={"page_size": 101})
        invalid_page_response = client.get("/products", params={"page": 0})

    assert oversized_response.status_code == 422
    assert invalid_page_response.status_code == 422
    assert oversized_response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert invalid_page_response.json()["error"]["code"] == "VALIDATION_ERROR"


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

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "INSUFFICIENT_STOCK",
        "message": "Estoque insuficiente",
    }

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
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_incorrect_movement_type_for_route_is_rejected():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "entry", "quantity": 1},
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MOVEMENT_TYPE"


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
