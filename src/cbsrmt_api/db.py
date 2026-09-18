from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool


class Database:
    def __init__(self, dsn: str, min_size: int = 1, max_size: int = 10) -> None:
        self.pool = ConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=False,
        )

    def open(self) -> None:
        self.pool.open(wait=True)

    def close(self) -> None:
        self.pool.close()

    @staticmethod
    def _adapt_params(params: Sequence[Any]) -> tuple[Any, ...]:
        return tuple(Jsonb(value) if isinstance(value, (dict, list)) else value for value in params)

    def scalar_json(self, sql: str, params: Sequence[Any] = ()) -> Any:
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.execute(sql, self._adapt_params(params))
            row = cur.fetchone()
            if row is None:
                return None
            return next(iter(row.values()))

    def execute_scalar(self, sql: str, params: Sequence[Any] = ()) -> Any:
        return self.scalar_json(sql, params)
