from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def run_migrations(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            create table if not exists schema_migrations (
              filename text primary key,
              applied_at timestamptz not null default now()
            )
            """
        )
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            applied = await conn.fetchval(
                "select 1 from schema_migrations where filename = $1",
                path.name,
            )
            if applied:
                continue
            sql = path.read_text(encoding="utf-8")
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "insert into schema_migrations (filename) values ($1)",
                    path.name,
                )
