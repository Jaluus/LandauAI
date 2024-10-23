import os

import chainlit.data as cl_data
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

CONN_STRING_TEMPLATE = "postgresql+asyncpg://{user}:{password}@{host}/{database}"

pg_username = os.getenv("PG_DB_USER", None)
pg_password = os.getenv("PG_DB_PASSWORD", None)
pg_db = os.getenv("PG_DB_NAME", None)
pg_host = os.getenv("PG_DB_HOST", "postgres")

if pg_username is None or pg_password is None or pg_db is None:
    raise ValueError(
        "Please set all environment variables PG_DB_USER, PG_DB_PASSWORD, PG_DB_NAME, and optionally PG_DB_HOST"
    )


cl_data._data_layer = SQLAlchemyDataLayer(
    CONN_STRING_TEMPLATE.format(
        user=pg_username,
        password=pg_password,
        host=pg_host,
        database=pg_db,
    )
)
