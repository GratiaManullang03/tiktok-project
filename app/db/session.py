from typing import Generator
import psycopg2
import psycopg2.extras

from app.core.config import settings


def get_connection() -> psycopg2.extensions.connection:
    """Open a new connection directly - for callers outside FastAPI's request scope
    (e.g. background tasks) that can't use the `get_db` dependency."""
    return psycopg2.connect(
        host=settings.PGHOST,
        dbname=settings.PGDATABASE,
        user=settings.PGUSER,
        password=settings.PGPASSWORD,
        sslmode=settings.PGSSLMODE,
        channel_binding=settings.PGCHANNELBINDING,
        connect_timeout=settings.PGCONNECT_TIMEOUT,
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    """Dependency to get a raw DB connection (dict-row cursor)."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
