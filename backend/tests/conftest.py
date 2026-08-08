import os

from sqlalchemy import create_engine

from app import database


os.environ["DEPOSITA_SECRET_KEY"] = "test-secret-key-for-deposita"


TEST_DATABASE_URL = "sqlite:///./test_deposita.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# app.main creates its tables during import. Point that initialization to the
# dedicated test database before pytest imports the application module.
database.engine = test_engine
