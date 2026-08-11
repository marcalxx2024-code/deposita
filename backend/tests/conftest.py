import os

from sqlalchemy import create_engine

from app import database
from app import models  # noqa: F401 - registers all models before creating test tables


os.environ["DEPOSITA_SECRET_KEY"] = "test-only-key-for-deposita-not-a-production-secret-2026"
os.environ["CORS_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"


TEST_DATABASE_URL = "sqlite:///./test_deposita.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Create the schema only in the dedicated test database. Production schema is
# managed by Alembic migrations.
database.engine = test_engine
database.Base.metadata.create_all(bind=test_engine)
