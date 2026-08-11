import os
from pathlib import Path

from dotenv import load_dotenv


# System environment variables take precedence over values in a local .env file.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_FILE, override=False)

DEFAULT_DATABASE_URL = "sqlite:///./deposita.db"
DEFAULT_DEMO_USERNAME = "demo"

TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "on"})
FALSE_ENV_VALUES = frozenset({"0", "false", "no", "off"})


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_demo_mode() -> bool:
    raw_value = os.getenv("DEMO_MODE", "false").strip().lower()
    if raw_value in TRUE_ENV_VALUES:
        return True
    if raw_value in FALSE_ENV_VALUES:
        return False
    raise ValueError(
        "DEMO_MODE must be one of: true, false, 1, 0, yes, no, on, off"
    )


def get_demo_username() -> str:
    username = os.getenv("DEMO_USERNAME", DEFAULT_DEMO_USERNAME).strip()
    if not username:
        raise ValueError("DEMO_USERNAME must not be empty")
    return username


def parse_cors_origins(value: str | None = None) -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "") if value is None else value
    origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must contain explicit origins")
    return origins
