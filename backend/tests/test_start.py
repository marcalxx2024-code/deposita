import subprocess
import sys

import pytest

from app import start


def test_prepare_database_runs_migrations_without_demo_reset(monkeypatch):
    calls = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, check: calls.append((command, check)),
    )
    monkeypatch.setattr(start, "get_demo_mode", lambda: False)
    monkeypatch.setattr(start, "seed_demo", pytest.fail)

    start.prepare_database()

    assert calls == [
        ([sys.executable, "-m", "alembic", "upgrade", "head"], True)
    ]


def test_prepare_database_resets_seed_only_in_demo_mode(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda _command, check: check)
    monkeypatch.setattr(start, "get_demo_mode", lambda: True)
    seed_calls = []
    monkeypatch.setattr(
        start,
        "seed_demo",
        lambda reset: seed_calls.append(reset),
    )

    start.prepare_database()

    assert seed_calls == [True]


def test_migration_failure_prevents_demo_seed(monkeypatch):
    def fail_migration(_command, check):
        raise subprocess.CalledProcessError(1, "alembic")

    monkeypatch.setattr(subprocess, "run", fail_migration)
    monkeypatch.setattr(start, "get_demo_mode", lambda: True)
    monkeypatch.setattr(start, "seed_demo", pytest.fail)

    with pytest.raises(subprocess.CalledProcessError):
        start.prepare_database()


def test_seed_failure_propagates_and_prevents_startup(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda _command, check: check)
    monkeypatch.setattr(start, "get_demo_mode", lambda: True)

    def fail_seed(reset):
        assert reset is True
        raise RuntimeError("seed failed")

    monkeypatch.setattr(start, "seed_demo", fail_seed)

    with pytest.raises(RuntimeError, match="seed failed"):
        start.prepare_database()


def test_server_command_uses_public_host_port_and_one_worker():
    command = start.server_command(10000)

    assert command == [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "10000",
        "--workers",
        "1",
    ]


@pytest.mark.parametrize("value", ["invalid", "0", "65536"])
def test_invalid_port_is_rejected(monkeypatch, value):
    monkeypatch.setenv("PORT", value)

    with pytest.raises(RuntimeError, match="PORT"):
        start.get_port()
