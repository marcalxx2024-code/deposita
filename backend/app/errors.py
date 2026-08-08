class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def product_not_found_error() -> APIError:
    return APIError(
        status_code=404,
        code="PRODUCT_NOT_FOUND",
        message="Produto não encontrado",
    )


def username_already_exists_error() -> APIError:
    return APIError(
        status_code=409,
        code="USERNAME_ALREADY_EXISTS",
        message="Nome de usuário já está em uso",
    )
