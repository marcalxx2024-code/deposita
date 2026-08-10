import json
import os
from datetime import datetime, timedelta, timezone
from itertools import count

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.config import parse_cors_origins
from app.main import app
from app.models import User, UserRole
from app.security import create_access_token, hash_password, verify_password


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
product_sku_counter = count(1)


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


def get_auth_headers(client: TestClient) -> dict[str, str]:
    headers = getattr(client, "_deposita_auth_headers", None)
    if headers is not None:
        return headers

    db = TestingSessionLocal()
    try:
        db.add(
            User(
                username="test-admin",
                password_hash=hash_password("uma-senha-segura"),
                role=UserRole.ADMIN.value,
            )
        )
        db.commit()
    finally:
        db.close()

    login_response = client.post(
        "/auth/login",
        json={"username": "test-admin", "password": "uma-senha-segura"},
    )
    assert login_response.status_code == 200

    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    client._deposita_auth_headers = headers
    return headers


def get_operator_headers(client: TestClient) -> dict[str, str]:
    create_user_response = client.post(
        "/users",
        json={"username": "test-operator", "password": "uma-senha-segura"},
    )
    assert create_user_response.status_code == 201
    login_response = client.post(
        "/auth/login",
        json={"username": "test-operator", "password": "uma-senha-segura"},
    )
    assert login_response.status_code == 200
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def create_product(
    client: TestClient,
    quantity: int,
    name: str = "Produto de teste",
    minimum_quantity: int = 2,
    sku: str | None = None,
    category: str = "Teste",
    price: float = 10.5,
    supplier_id: int | None = None,
) -> dict:
    response = client.post(
        "/products",
        json={
            "name": name,
            "category": category,
            "quantity": quantity,
            "minimum_quantity": minimum_quantity,
            "price": price,
            "sku": sku or f"TEST-{next(product_sku_counter)}",
            "supplier_id": supplier_id,
        },
        headers=get_auth_headers(client),
    )
    assert response.status_code == 200
    return response.json()


def test_create_product_returns_id():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

    assert isinstance(product["id"], int)


def test_parse_cors_origins_accepts_single_multiple_and_spaced_values():
    assert parse_cors_origins("http://frontend.test") == ["http://frontend.test"]
    assert parse_cors_origins("http://one.test,http://two.test") == [
        "http://one.test",
        "http://two.test",
    ]
    assert parse_cors_origins(" http://one.test , http://two.test ") == [
        "http://one.test",
        "http://two.test",
    ]


def test_parse_cors_origins_returns_no_origins_for_empty_configuration():
    assert parse_cors_origins("") == []
    assert parse_cors_origins("   ") == []


def test_cors_allows_configured_origin_only_and_never_returns_the_secret_key():
    with TestClient(app) as client:
        allowed_response = client.options(
            "/products",
            headers={
                "Origin": "http://frontend.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied_response = client.options(
            "/products",
            headers={
                "Origin": "http://untrusted.test",
                "Access-Control-Request-Method": "GET",
            },
        )
        response = client.get("/health", headers={"Origin": "http://frontend.test"})

    assert allowed_response.status_code == 200
    assert allowed_response.headers["access-control-allow-origin"] == "http://frontend.test"
    assert "access-control-allow-credentials" not in allowed_response.headers
    assert denied_response.status_code == 400
    assert "access-control-allow-origin" not in denied_response.headers
    assert response.status_code == 200
    assert os.environ["DEPOSITA_SECRET_KEY"] not in response.text


def test_write_endpoints_require_authentication():
    product_data = {
        "name": "Produto protegido",
        "category": "Teste",
        "quantity": 10,
        "minimum_quantity": 2,
        "price": 10.5,
        "sku": "PROTEGIDO-01",
    }
    update_data = {
        "name": "Produto protegido",
        "category": "Teste",
        "minimum_quantity": 2,
        "price": 10.5,
    }

    with TestClient(app) as client:
        responses = (
            client.post("/products", json=product_data),
            client.put("/products/999999", json=update_data),
            client.delete("/products/999999"),
            client.post(
                "/products/999999/movements/entry",
                json={"movement_type": "entry", "quantity": 1},
            ),
            client.post(
                "/products/999999/movements/exit",
                json={"movement_type": "exit", "quantity": 1},
            ),
        )

    for response in responses:
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_AUTHENTICATION"
        assert response.headers["www-authenticate"] == "Bearer"


def test_admin_can_execute_all_write_endpoints():
    product_data = {
        "name": "Produto protegido",
        "category": "Teste",
        "quantity": 10,
        "minimum_quantity": 2,
        "price": 10.5,
        "sku": "PROTEGIDO-ADMIN-01",
    }
    update_data = {
        "name": "Produto atualizado",
        "category": "Teste",
        "minimum_quantity": 3,
        "price": 12.0,
    }

    with TestClient(app) as client:
        headers = get_auth_headers(client)
        create_response = client.post("/products", json=product_data, headers=headers)
        product_id = create_response.json()["id"]
        update_response = client.put(
            f"/products/{product_id}", json=update_data, headers=headers
        )
        entry_response = client.post(
            f"/products/{product_id}/movements/entry",
            json={"movement_type": "entry", "quantity": 2},
            headers=headers,
        )
        exit_response = client.post(
            f"/products/{product_id}/movements/exit",
            json={"movement_type": "exit", "quantity": 1},
            headers=headers,
        )
        delete_response = client.delete(f"/products/{product_id}", headers=headers)

    assert create_response.status_code == 200
    assert update_response.status_code == 200
    assert entry_response.status_code == 201
    assert exit_response.status_code == 201
    assert delete_response.status_code == 200


def test_operator_can_create_stock_movements_but_not_manage_products():
    update_data = {
        "name": "Produto atualizado",
        "category": "Teste",
        "minimum_quantity": 2,
        "price": 10.5,
    }

    with TestClient(app) as client:
        product = create_product(client, quantity=10)
        operator_headers = get_operator_headers(client)
        entry_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 2},
            headers=operator_headers,
        )
        exit_response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 1},
            headers=operator_headers,
        )
        create_response = client.post(
            "/products",
            json={
                "name": "Produto do operador",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
            },
            headers=operator_headers,
        )
        update_response = client.put(
            f"/products/{product['id']}", json=update_data, headers=operator_headers
        )
        delete_response = client.delete(
            f"/products/{product['id']}", headers=operator_headers
        )

    assert entry_response.status_code == 201
    assert exit_response.status_code == 201
    for response in (create_response, update_response, delete_response):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "FORBIDDEN"


def test_role_changes_in_the_database_apply_to_existing_tokens():
    with TestClient(app) as client:
        operator_headers = get_operator_headers(client)
        product_data = {
            "name": "Produto protegido",
            "category": "Teste",
            "quantity": 10,
            "minimum_quantity": 2,
            "price": 10.5,
            "sku": "PROTEGIDO-01",
        }
        denied_response = client.post(
            "/products", json=product_data, headers=operator_headers
        )

        db = TestingSessionLocal()
        try:
            operator = db.query(User).filter(User.username == "test-operator").one()
            operator.role = UserRole.ADMIN.value
            db.commit()
        finally:
            db.close()

        allowed_response = client.post(
            "/products", json=product_data, headers=operator_headers
        )

    assert denied_response.status_code == 403
    assert allowed_response.status_code == 200


def test_valid_token_for_missing_user_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/products",
            json={
                "name": "Produto protegido",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
            },
            headers={"Authorization": f"Bearer {create_access_token('999999')}"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTHENTICATION"


def test_write_endpoints_reject_tampered_tokens():
    with TestClient(app) as client:
        response = client.post(
            "/products",
            json={
                "name": "Produto protegido",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
            },
            headers={"Authorization": "Bearer token-adulterado"},
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTHENTICATION"


def test_read_endpoints_remain_public():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)
        health_response = client.get("/health")
        list_response = client.get("/products")
        product_response = client.get(f"/products/{product['id']}")
        low_stock_response = client.get("/products/low-stock")
        movements_response = client.get("/movements")
        dashboard_response = client.get("/dashboard/summary")

    for response in (
        health_response,
        list_response,
        product_response,
        low_stock_response,
        movements_response,
        dashboard_response,
    ):
        assert response.status_code == 200


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
    assert user_response["role"] == "operator"
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


def test_create_user_does_not_accept_a_client_selected_role():
    with TestClient(app) as client:
        response = client.post(
            "/users",
            json={
                "username": "guilherme",
                "password": "uma-senha-segura",
                "role": "admin",
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


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
        headers = get_auth_headers(client)
        get_response = client.get("/products/999")
        update_response = client.put("/products/999", json=product_data, headers=headers)
        delete_response = client.delete("/products/999", headers=headers)

    for response in (get_response, update_response, delete_response):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
        assert response.json()["error"]["message"] == "Produto não encontrado"


def test_invalid_payload_returns_safe_validation_details():
    with TestClient(app) as client:
        headers = get_auth_headers(client)
        response = client.post(
            "/products",
            json={
                "name": "A",
                "category": "",
                "quantity": -1,
                "minimum_quantity": -1,
                "price": -1,
                "sku": "INVALIDO-01",
            },
            headers=headers,
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


def test_error_responses_use_a_safe_and_consistent_envelope():
    product_data = {
        "name": "Produto de erro",
        "category": "Teste",
        "quantity": 1,
        "minimum_quantity": 0,
        "price": 10,
        "sku": "ERROR-001",
    }
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        operator_headers = get_operator_headers(client)
        unauthorized_response = client.get("/auth/me")
        forbidden_response = client.post(
            "/products", json=product_data, headers=operator_headers
        )
        not_found_response = client.get("/products/999")
        first_user_response = client.post(
            "/users", json={"username": "duplicado", "password": "uma-senha-segura"}
        )
        conflict_response = client.post(
            "/users", json={"username": "duplicado", "password": "outra-senha-segura"}
        )
        validation_response = client.get(
            "/products", params={"min_price": 20, "max_price": 10}
        )
        invalid_movement_response = client.post(
            "/products/999/movements/entry",
            json={"movement_type": "exit", "quantity": 1},
            headers=admin_headers,
        )

    assert first_user_response.status_code == 201
    expected_codes = (
        (unauthorized_response, 401, "INVALID_AUTHENTICATION"),
        (forbidden_response, 403, "FORBIDDEN"),
        (not_found_response, 404, "PRODUCT_NOT_FOUND"),
        (conflict_response, 409, "USERNAME_ALREADY_EXISTS"),
        (validation_response, 422, "VALIDATION_ERROR"),
        (invalid_movement_response, 400, "INVALID_MOVEMENT_TYPE"),
    )
    for response, status_code, code in expected_codes:
        assert response.status_code == status_code
        assert set(response.json()) == {"error"}
        assert response.json()["error"]["code"] == code
        assert isinstance(response.json()["error"]["message"], str)

        serialized_error = json.dumps(response.json()).lower()
        for sensitive_value in ("password", "secret", "token", "traceback", "sqlite"):
            assert sensitive_value not in serialized_error

    validation_error = validation_response.json()["error"]
    assert validation_error["details"] == [
        {
            "field": "query.max_price",
            "message": "max_price deve ser maior ou igual a min_price",
            "type": "value_error",
        }
    ]


def test_product_validation_rejects_blank_negative_and_oversized_values():
    invalid_products = (
        {"name": "   "},
        {"category": "   "},
        {"price": -0.01},
        {"quantity": -1},
        {"minimum_quantity": -1},
        {"sku": "S" * 65},
        {"name": "N" * 101},
        {"category": "C" * 51},
    )
    valid_product = {
        "name": "  Produto válido  ",
        "category": "  Categoria  ",
        "quantity": 1,
        "minimum_quantity": 0,
        "price": 0,
        "sku": "  valid-001  ",
    }

    with TestClient(app) as client:
        headers = get_auth_headers(client)
        responses = []
        for invalid_fields in invalid_products:
            payload = {**valid_product, **invalid_fields}
            responses.append(client.post("/products", json=payload, headers=headers))
        valid_response = client.post("/products", json=valid_product, headers=headers)

    assert all(response.status_code == 422 for response in responses)
    assert valid_response.status_code == 200
    assert valid_response.json()["name"] == "Produto válido"
    assert valid_response.json()["category"] == "Categoria"
    assert valid_response.json()["sku"] == "VALID-001"


def test_supplier_validation_rejects_blank_invalid_and_oversized_fields():
    valid_supplier = {
        "name": "  Fornecedor válido  ",
        "contact_name": "  Contato  ",
        "phone": "  11999999999  ",
        "email": "  CONTATO@FORNECEDOR.TEST  ",
    }
    invalid_suppliers = (
        {"name": "   "},
        {"contact_name": "   "},
        {"email": "email-inválido"},
        {"phone": "1" * 31},
        {"email": "e" * 256},
    )

    with TestClient(app) as client:
        headers = get_auth_headers(client)
        responses = []
        for invalid_fields in invalid_suppliers:
            payload = {**valid_supplier, **invalid_fields}
            responses.append(client.post("/suppliers", json=payload, headers=headers))
        valid_response = client.post("/suppliers", json=valid_supplier, headers=headers)

    assert all(response.status_code == 422 for response in responses)
    assert valid_response.status_code == 201
    assert valid_response.json()["name"] == "Fornecedor válido"
    assert valid_response.json()["contact_name"] == "Contato"
    assert valid_response.json()["phone"] == "11999999999"
    assert valid_response.json()["email"] == "contato@fornecedor.test"


def test_movement_validation_rejects_non_positive_and_oversized_note():
    with TestClient(app) as client:
        product = create_product(client, quantity=2)
        headers = get_auth_headers(client)
        zero_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 0},
            headers=headers,
        )
        negative_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": -1},
            headers=headers,
        )
        note_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 1, "note": "N" * 256},
            headers=headers,
        )
        valid_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 1, "note": "  Reposição  "},
            headers=headers,
        )

    assert zero_response.status_code == 422
    assert negative_response.status_code == 422
    assert note_response.status_code == 422
    assert valid_response.status_code == 201
    assert valid_response.json()["note"] == "Reposição"


def test_user_validation_rejects_oversized_username_and_keeps_valid_input():
    with TestClient(app) as client:
        empty_username_response = client.post(
            "/users", json={"username": "   ", "password": "uma-senha-segura"}
        )
        short_password_response = client.post(
            "/users", json={"username": "usuario-curto", "password": "curta"}
        )
        oversized_response = client.post(
            "/users", json={"username": "u" * 101, "password": "uma-senha-segura"}
        )
        valid_response = client.post(
            "/users",
            json={"username": "  usuario-valido  ", "password": "uma-senha-segura"},
        )

    assert empty_username_response.status_code == 422
    assert short_password_response.status_code == 422
    assert oversized_response.status_code == 422
    assert valid_response.status_code == 201
    assert valid_response.json()["username"] == "usuario-valido"


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


def test_list_products_filters_by_category_supplier_price_and_combination():
    with TestClient(app) as client:
        headers = get_auth_headers(client)
        supplier_response = client.post(
            "/suppliers", json={"name": "Fornecedor A"}, headers=headers
        )
        assert supplier_response.status_code == 201
        supplier_id = supplier_response.json()["id"]
        matching_product = create_product(
            client,
            quantity=1,
            minimum_quantity=2,
            name="Cabo premium",
            category="Eletrônicos",
            price=25.0,
            supplier_id=supplier_id,
        )
        second_supplier_product = create_product(
            client,
            quantity=4,
            category="Eletrônicos",
            price=30.0,
            supplier_id=supplier_id,
        )
        create_product(client, quantity=1, category="Papelaria", price=25.0)

        category_response = client.get("/products", params={"category": "Eletrônicos"})
        supplier_response = client.get("/products", params={"supplier_id": supplier_id})
        price_response = client.get(
            "/products", params={"min_price": 24, "max_price": 26}
        )
        combined_response = client.get(
            "/products",
            params={
                "search": "cabo",
                "category": "Eletrônicos",
                "supplier_id": supplier_id,
                "low_stock": True,
                "min_price": 20,
                "max_price": 30,
            },
        )

    assert [item["id"] for item in category_response.json()["items"]] == [
        matching_product["id"],
        second_supplier_product["id"],
    ]
    assert supplier_response.json()["total"] == 2
    assert price_response.json()["total"] == 2
    assert [item["id"] for item in combined_response.json()["items"]] == [
        matching_product["id"]
    ]


def test_list_products_validates_price_range_and_supplier_filter():
    with TestClient(app) as client:
        negative_min_response = client.get("/products", params={"min_price": -1})
        negative_max_response = client.get("/products", params={"max_price": -1})
        invalid_range_response = client.get(
            "/products", params={"min_price": 20, "max_price": 10}
        )
        missing_supplier_response = client.get(
            "/products", params={"supplier_id": 999}
        )

    assert negative_min_response.status_code == 422
    assert negative_max_response.status_code == 422
    assert invalid_range_response.status_code == 422
    assert missing_supplier_response.status_code == 404
    assert missing_supplier_response.json()["error"]["code"] == "SUPPLIER_NOT_FOUND"


def test_list_products_sorts_with_safe_whitelist_and_keeps_sku_search():
    with TestClient(app) as client:
        expensive_product = create_product(
            client, quantity=8, name="Zulu", price=30, sku="SKU-ZULU"
        )
        cheap_product = create_product(
            client, quantity=2, name="Alfa", price=10, sku="SKU-ALFA"
        )

        ascending_response = client.get(
            "/products", params={"sort_by": "price", "sort_order": "asc"}
        )
        descending_response = client.get(
            "/products", params={"sort_by": "price", "sort_order": "desc"}
        )
        sku_response = client.get("/products", params={"search": "alfa"})
        invalid_sort_response = client.get(
            "/products", params={"sort_by": "supplier_id"}
        )
        invalid_order_response = client.get(
            "/products", params={"sort_order": "sideways"}
        )

    assert [item["id"] for item in ascending_response.json()["items"]] == [
        cheap_product["id"],
        expensive_product["id"],
    ]
    assert [item["id"] for item in descending_response.json()["items"]] == [
        expensive_product["id"],
        cheap_product["id"],
    ]
    assert [item["id"] for item in sku_response.json()["items"]] == [cheap_product["id"]]
    assert invalid_sort_response.status_code == 422
    assert invalid_order_response.status_code == 422


def test_create_stock_entry_updates_product_quantity():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 5, "note": "Reposição"},
            headers=get_auth_headers(client),
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
            headers=get_auth_headers(client),
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
            headers=get_auth_headers(client),
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
            headers=get_auth_headers(client),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_incorrect_movement_type_for_route_is_rejected():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "entry", "quantity": 1},
            headers=get_auth_headers(client),
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_MOVEMENT_TYPE"


def test_list_stock_movements_returns_most_recent_first():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)

        entry_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 5},
            headers=get_auth_headers(client),
        )
        exit_response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 4},
            headers=get_auth_headers(client),
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
                "sku": "ESTOQUE-ACIMA",
            },
            headers=get_auth_headers(client),
        )
        equal_to_minimum = client.post(
            "/products",
            json={
                "name": "Estoque mínimo",
                "category": "Teste",
                "quantity": 3,
                "minimum_quantity": 3,
                "price": 10.0,
                "sku": "ESTOQUE-MINIMO",
            },
            headers=get_auth_headers(client),
        )
        below_minimum = client.post(
            "/products",
            json={
                "name": "Estoque baixo",
                "category": "Teste",
                "quantity": 1,
                "minimum_quantity": 2,
                "price": 10.0,
                "sku": "ESTOQUE-BAIXO",
            },
            headers=get_auth_headers(client),
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
            "sku": "ESTOQUE-NORMAL",
        },
        {
            "name": "Estoque baixo",
            "category": "Teste",
            "quantity": 2,
            "minimum_quantity": 2,
            "price": 3.25,
            "sku": "ESTOQUE-BAIXO",
        },
        {
            "name": "Estoque zerado",
            "category": "Teste",
            "quantity": 0,
            "minimum_quantity": 1,
            "price": 7.0,
            "sku": "ESTOQUE-ZERADO",
        },
    ]

    with TestClient(app) as client:
        for product in products:
            create_response = client.post(
                "/products", json=product, headers=get_auth_headers(client)
            )
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
                headers=get_auth_headers(client),
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


def test_audit_logs_record_product_and_stock_actions():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        product = create_product(client, quantity=10)

        update_response = client.put(
            f"/products/{product['id']}",
            json={
                "name": "Produto atualizado",
                "category": "Teste",
                "minimum_quantity": 3,
                "price": 12.0,
            },
            headers=admin_headers,
        )
        entry_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 2},
            headers=admin_headers,
        )
        exit_response = client.post(
            f"/products/{product['id']}/movements/exit",
            json={"movement_type": "exit", "quantity": 1},
            headers=admin_headers,
        )
        delete_response = client.delete(
            f"/products/{product['id']}", headers=admin_headers
        )
        audit_response = client.get("/audit-logs", headers=admin_headers)

    assert update_response.status_code == 200
    assert entry_response.status_code == 201
    assert exit_response.status_code == 201
    assert delete_response.status_code == 200
    assert audit_response.status_code == 200

    audit_logs = audit_response.json()
    assert [audit_log["action"] for audit_log in audit_logs] == [
        "product_deleted",
        "stock_exit",
        "stock_entry",
        "product_updated",
        "product_created",
    ]
    assert all(audit_log["resource_type"] == "product" for audit_log in audit_logs)
    assert all(audit_log["resource_id"] == product["id"] for audit_log in audit_logs)


def test_operator_stock_movement_is_audited():
    with TestClient(app) as client:
        product = create_product(client, quantity=10)
        operator_headers = get_operator_headers(client)
        entry_response = client.post(
            f"/products/{product['id']}/movements/entry",
            json={"movement_type": "entry", "quantity": 2},
            headers=operator_headers,
        )
        audit_response = client.get(
            "/audit-logs", headers=get_auth_headers(client)
        )

    assert entry_response.status_code == 201
    db = TestingSessionLocal()
    try:
        operator = db.query(User).filter(User.username == "test-operator").one()
    finally:
        db.close()
    operator_log = next(
        audit_log
        for audit_log in audit_response.json()
        if audit_log["action"] == "stock_entry"
    )
    assert operator_log["user_id"] == operator.id
    assert operator_log["resource_id"] == product["id"]


def test_operator_cannot_list_audit_logs():
    with TestClient(app) as client:
        response = client.get("/audit-logs", headers=get_operator_headers(client))

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_admin_can_list_audit_logs_without_sensitive_data():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        create_product(client, quantity=10)
        response = client.get("/audit-logs", headers=admin_headers)

    assert response.status_code == 200
    audit_log = response.json()[0]
    assert set(audit_log) == {
        "id",
        "user_id",
        "action",
        "resource_type",
        "resource_id",
        "created_at",
    }
    serialized_response = json.dumps(response.json())
    for sensitive_field in ("password", "token", "secret", "jwt"):
        assert sensitive_field not in serialized_response.lower()


def test_admin_can_create_update_list_and_delete_suppliers_with_audit_logs():
    supplier_data = {
        "name": "Fornecedor de teste",
        "contact_name": "Contato",
        "phone": "11999999999",
        "email": "contato@fornecedor.test",
    }
    updated_supplier_data = {
        **supplier_data,
        "name": "Fornecedor atualizado",
        "phone": "11888888888",
    }

    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        create_response = client.post(
            "/suppliers", json=supplier_data, headers=admin_headers
        )
        supplier_id = create_response.json()["id"]
        list_response = client.get("/suppliers", headers=admin_headers)
        detail_response = client.get(f"/suppliers/{supplier_id}", headers=admin_headers)
        update_response = client.put(
            f"/suppliers/{supplier_id}",
            json=updated_supplier_data,
            headers=admin_headers,
        )
        delete_response = client.delete(f"/suppliers/{supplier_id}", headers=admin_headers)
        audit_response = client.get("/audit-logs", headers=admin_headers)

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Fornecedor atualizado"
    assert delete_response.status_code == 200
    assert [supplier["id"] for supplier in list_response.json()] == [supplier_id]
    assert [audit_log["action"] for audit_log in audit_response.json()] == [
        "supplier_deleted",
        "supplier_updated",
        "supplier_created",
    ]
    assert all(audit_log["resource_type"] == "supplier" for audit_log in audit_response.json())
    assert all(audit_log["resource_id"] == supplier_id for audit_log in audit_response.json())


def test_operator_cannot_create_supplier():
    with TestClient(app) as client:
        response = client.post(
            "/suppliers",
            json={"name": "Fornecedor de teste"},
            headers=get_operator_headers(client),
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_supplier_not_found_returns_404():
    supplier_data = {"name": "Fornecedor de teste"}

    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        responses = (
            client.get("/suppliers/999", headers=admin_headers),
            client.put("/suppliers/999", json=supplier_data, headers=admin_headers),
            client.delete("/suppliers/999", headers=admin_headers),
        )

    for response in responses:
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUPPLIER_NOT_FOUND"


def test_products_can_optionally_reference_a_supplier_and_validate_supplier_id():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        supplier_response = client.post(
            "/suppliers", json={"name": "Fornecedor de teste"}, headers=admin_headers
        )
        supplier_id = supplier_response.json()["id"]
        product_with_supplier = client.post(
            "/products",
            json={
                "name": "Produto com fornecedor",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
                "supplier_id": supplier_id,
                "sku": "COM-FORNECEDOR",
            },
            headers=admin_headers,
        )
        product_without_supplier = create_product(client, quantity=10)
        invalid_supplier_response = client.post(
            "/products",
            json={
                "name": "Produto invalido",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
                "supplier_id": 999,
                "sku": "FORNECEDOR-INVALIDO",
            },
            headers=admin_headers,
        )
        invalid_update_response = client.put(
            f"/products/{product_without_supplier['id']}",
            json={
                "name": "Produto atualizado",
                "category": "Teste",
                "minimum_quantity": 2,
                "price": 10.5,
                "supplier_id": 999,
            },
            headers=admin_headers,
        )

    assert supplier_response.status_code == 201
    assert product_with_supplier.status_code == 200
    assert product_with_supplier.json()["supplier_id"] == supplier_id
    assert product_without_supplier["supplier_id"] is None
    assert invalid_supplier_response.status_code == 404
    assert invalid_supplier_response.json()["error"]["code"] == "SUPPLIER_NOT_FOUND"
    assert invalid_update_response.status_code == 404
    assert invalid_update_response.json()["error"]["code"] == "SUPPLIER_NOT_FOUND"


def test_cannot_delete_supplier_associated_with_a_product():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        supplier_response = client.post(
            "/suppliers", json={"name": "Fornecedor de teste"}, headers=admin_headers
        )
        supplier_id = supplier_response.json()["id"]
        product_response = client.post(
            "/products",
            json={
                "name": "Produto associado",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
                "supplier_id": supplier_id,
                "sku": "PRODUTO-ASSOCIADO",
            },
            headers=admin_headers,
        )
        delete_response = client.delete(f"/suppliers/{supplier_id}", headers=admin_headers)
        product_after_delete_attempt = client.get(
            f"/products/{product_response.json()['id']}"
        )

    assert delete_response.status_code == 409
    assert delete_response.json()["error"]["code"] == "SUPPLIER_IN_USE"
    assert product_after_delete_attempt.status_code == 200
    assert product_after_delete_attempt.json()["supplier_id"] == supplier_id


def test_product_sku_is_required_normalized_and_returned():
    product_data = {
        "name": "Cabo HDMI",
        "category": "Cabos",
        "quantity": 10,
        "minimum_quantity": 2,
        "price": 10.5,
        "sku": "  cabo-hdmi-02  ",
    }

    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        create_response = client.post(
            "/products", json=product_data, headers=admin_headers
        )
        invalid_response = client.post(
            "/products",
            json={**product_data, "name": "Produto invalido", "sku": "   "},
            headers=admin_headers,
        )

    assert create_response.status_code == 200
    assert create_response.json()["sku"] == "CABO-HDMI-02"
    assert invalid_response.status_code == 422
    assert invalid_response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_product_creation_rejects_duplicate_sku():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        first_product = create_product(client, quantity=10, sku="BEB-0001")
        duplicate_response = client.post(
            "/products",
            json={
                "name": "Outro produto",
                "category": "Teste",
                "quantity": 10,
                "minimum_quantity": 2,
                "price": 10.5,
                "sku": " beb-0001 ",
            },
            headers=admin_headers,
        )

    assert first_product["sku"] == "BEB-0001"
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "SKU_ALREADY_EXISTS"


def test_product_sku_can_be_updated_and_searched():
    with TestClient(app) as client:
        admin_headers = get_auth_headers(client)
        product = create_product(client, quantity=10, sku="PROD-ANTIGO")
        other_product = create_product(client, quantity=10, sku="PROD-OUTRO")
        update_payload = {
            "name": "Produto atualizado",
            "category": "Teste",
            "minimum_quantity": 2,
            "price": 10.5,
            "sku": " prod-novo ",
        }
        update_response = client.put(
            f"/products/{product['id']}", json=update_payload, headers=admin_headers
        )
        duplicate_update_response = client.put(
            f"/products/{other_product['id']}",
            json={**update_payload, "sku": "PROD-NOVO"},
            headers=admin_headers,
        )
        search_response = client.get("/products", params={"search": "novo"})

    assert update_response.status_code == 200
    assert update_response.json()["sku"] == "PROD-NOVO"
    assert duplicate_update_response.status_code == 409
    assert duplicate_update_response.json()["error"]["code"] == "SKU_ALREADY_EXISTS"
    assert [item["id"] for item in search_response.json()["items"]] == [product["id"]]
