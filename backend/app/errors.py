class APIError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers


def product_not_found_error() -> APIError:
    return APIError(
        status_code=404,
        code="PRODUCT_NOT_FOUND",
        message="Produto não encontrado",
    )


def sku_already_exists_error() -> APIError:
    return APIError(
        status_code=409,
        code="SKU_ALREADY_EXISTS",
        message="SKU jÃ¡ estÃ¡ em uso",
    )


def supplier_not_found_error() -> APIError:
    return APIError(
        status_code=404,
        code="SUPPLIER_NOT_FOUND",
        message="Fornecedor nÃ£o encontrado",
    )


def supplier_in_use_error() -> APIError:
    return APIError(
        status_code=409,
        code="SUPPLIER_IN_USE",
        message="Fornecedor possui produtos associados",
    )


def username_already_exists_error() -> APIError:
    return APIError(
        status_code=409,
        code="USERNAME_ALREADY_EXISTS",
        message="Nome de usuário já está em uso",
    )


def invalid_credentials_error() -> APIError:
    return APIError(
        status_code=401,
        code="INVALID_CREDENTIALS",
        message="Credenciais inválidas",
    )


def invalid_authentication_error() -> APIError:
    return APIError(
        status_code=401,
        code="INVALID_AUTHENTICATION",
        message="Não foi possível autenticar a solicitação",
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_error() -> APIError:
    return APIError(
        status_code=403,
        code="FORBIDDEN",
        message="Você não tem permissão para esta operação",
    )
