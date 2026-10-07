"""Run Alembic migrations exactly once even when several replicas start together.

Waits for the database, takes a PostgreSQL advisory lock so concurrent init containers
queue up instead of racing, then runs `alembic upgrade head`.
"""
import sys
import time

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.config import settings

LOCK_ID = 7_2026_1  # arbitrary, shared by every TicketHub instance


def wait_for_db(engine, attempts=30):
    for i in range(attempts):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[migrate] database not ready ({exc.__class__.__name__}), retry {i + 1}/{attempts}", flush=True)
            time.sleep(2)
    sys.exit("[migrate] database never became reachable")


def main():
    engine = create_engine(settings.database_url)
    wait_for_db(engine)
    cfg = Config("alembic.ini")
    if settings.database_url.startswith("postgresql"):
        with engine.connect() as conn:
            conn.execute(text("SELECT pg_advisory_lock(:id)"), {"id": LOCK_ID})
            print("[migrate] lock acquired, upgrading to head", flush=True)
            command.upgrade(cfg, "head")
            conn.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": LOCK_ID})
    else:
        command.upgrade(cfg, "head")
    print("[migrate] done", flush=True)


if __name__ == "__main__":
    main()
