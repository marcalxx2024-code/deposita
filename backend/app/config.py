import os
from pathlib import Path

from dotenv import load_dotenv


# System environment variables take precedence over values in a local .env file.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE, override=False)

DEFAULT_DATABASE_URL = "sqlite:///./deposita.db"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def parse_cors_origins(value: str | None = None) -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "") if value is None else value
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must contain explicit origins")
    return origins
