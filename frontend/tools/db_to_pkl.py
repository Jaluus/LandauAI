import asyncio
import os
import pickle

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.sql import text

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:9669/postgres"


async def main(url):
    engine = create_async_engine(url)
    db_entries = {
        "users": None,
        "threads": None,
        "steps": None,
        "feedbacks": None,
    }
    async with engine.connect() as conn:
        for key in db_entries:
            statement = text(f"SELECT * FROM {key}")
            res = await conn.execute(statement)
            db_entries[key] = res.fetchall()
    await engine.dispose()

    return db_entries


db_entries = asyncio.run(main(DB_URL))

file_dir = os.path.dirname(os.path.realpath(__file__))
pickle.dump(db_entries, open(f"{file_dir}/db_entries.pkl", "wb"))
