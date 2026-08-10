import sqlite3
import unicodedata

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_database_url


DATABASE_URL = get_database_url()


def normalize_search_text(value: str | None) -> str:
    if value is None:
        return ""

    normalized_value = unicodedata.normalize("NFD", value)
    return "".join(
        character
        for character in normalized_value
        if not unicodedata.combining(character)
    ).casefold()


@event.listens_for(Engine, "connect")
def register_sqlite_functions(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
        finally:
            cursor.close()
        dbapi_connection.create_function("normalize_search_text", 1, normalize_search_text)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
