import os
import subprocess
import sys

from app.config import get_demo_mode
from app.seed_demo import seed_demo


DEFAULT_PORT = 8000


def get_port() -> int:
    raw_port = os.getenv("PORT", str(DEFAULT_PORT))
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise RuntimeError("PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be between 1 and 65535")
    return port


def prepare_database() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )
    if get_demo_mode():
        seed_demo(reset=True)


def server_command(port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
        "--workers",
        "1",
    ]


def main() -> None:
    port = get_port()
    prepare_database()
    command = server_command(port)
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
