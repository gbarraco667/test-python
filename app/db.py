import asyncio
import logging
import os

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

log = logging.getLogger("db")

# Si no hay DATABASE_URL, libpq toma PGHOST, PGUSER, PGPASSWORD, PGDATABASE y PGPORT del entorno.
_conninfo = os.getenv("DATABASE_URL", "")
_kwargs = {"row_factory": dict_row, "connect_timeout": 5, "autocommit": True}
if os.getenv("DATABASE_SSL") == "true":
    _kwargs["sslmode"] = "require"

pool = AsyncConnectionPool(_conninfo, min_size=1, max_size=10, kwargs=_kwargs, open=False)


async def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    async with pool.connection() as conn:
        cur = await conn.execute(sql, params)
        return await cur.fetchone()


async def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    async with pool.connection() as conn:
        cur = await conn.execute(sql, params)
        return await cur.fetchall()


async def wait_for_database(retries: int = 15, delay: float = 2.0) -> None:
    await pool.open(wait=False)
    for attempt in range(1, retries + 1):
        try:
            await fetch_one("SELECT 1")
            log.info("conexión establecida")
            return
        except Exception as err:
            log.warning("intento %d/%d falló: %s", attempt, retries, err)
            if attempt == retries:
                raise
            await asyncio.sleep(delay)


async def migrate() -> None:
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
              id         SERIAL PRIMARY KEY,
              author     VARCHAR(60)  NOT NULL,
              content    VARCHAR(280) NOT NULL,
              created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS visits (
              id         SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
              total      BIGINT NOT NULL DEFAULT 0
            );

            INSERT INTO visits (id, total) VALUES (1, 0) ON CONFLICT (id) DO NOTHING;
        """)
    log.info("migraciones aplicadas")
