import argparse
import getpass
import sys

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import SessionLocal
from app.security import hash_password


class BootstrapAdminError(RuntimeError):
    pass


def bootstrap_admin(
    username: str, password: str, db: Session | None = None
) -> models.User:
    """Create the first administrator and refuse once any administrator exists."""
    user_data = schemas.UserCreate(username=username, password=password)
    session = db or SessionLocal()
    owns_session = db is None

    try:
        if (
            session.query(models.User)
            .filter(models.User.role == models.UserRole.ADMIN.value)
            .first()
            is not None
        ):
            raise BootstrapAdminError("Já existe um usuário ADMIN neste banco")

        if session.query(models.User).filter(models.User.username == user_data.username).first():
            raise BootstrapAdminError("Nome de usuário já está em uso")

        admin = models.User(
            username=user_data.username,
            password_hash=hash_password(user_data.password),
            role=models.UserRole.ADMIN.value,
        )
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin
    except Exception:
        session.rollback()
        raise
    finally:
        if owns_session:
            session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cria o primeiro ADMIN do Deposita")
    parser.add_argument("--username", required=True, help="Nome de usuário do ADMIN")
    args = parser.parse_args()

    password = getpass.getpass("Senha do ADMIN: ")
    password_confirmation = getpass.getpass("Confirme a senha: ")
    if password != password_confirmation:
        print("As senhas não conferem.", file=sys.stderr)
        return 1

    try:
        admin = bootstrap_admin(args.username, password)
    except ValidationError as exc:
        for error in exc.errors():
            print(error["msg"], file=sys.stderr)
        return 1
    except BootstrapAdminError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"ADMIN '{admin.username}' criado com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
