import json
from typing import Any, Dict, List, Optional, Tuple
import psycopg2.extras


class BaseRepository:
    """Raw-SQL CRUD helpers shared by every repository.

    Table/column names come from ERDRULES.md - each subclass just supplies
    its fully-qualified table name and primary key column.

    None of these methods commit. Multi-statement writes need to be atomic
    (e.g. upsert product + insert metric snapshot + insert score), so the
    caller owns the transaction boundary: commit once everything succeeded,
    rollback on the first failure.
    """

    def __init__(self, table: str, pk_column: str):
        self.table = table
        self.pk_column = pk_column

    def get(self, db, id_: Any) -> Optional[psycopg2.extras.RealDictRow]:
        with db.cursor() as cur:
            cur.execute(f"SELECT * FROM {self.table} WHERE {self.pk_column} = %(id)s", {"id": id_})
            return cur.fetchone()

    def get_multi(self, db, skip: int = 0, limit: int = 100) -> List[psycopg2.extras.RealDictRow]:
        with db.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self.table} "
                f"ORDER BY {self.pk_column} DESC OFFSET %(skip)s LIMIT %(limit)s",
                {"skip": skip, "limit": limit},
            )
            return cur.fetchall()

    def create(self, db, data: Dict[str, Any]) -> psycopg2.extras.RealDictRow:
        params, casts = self._prepare(data)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"%({key})s{casts[key]}" for key in data.keys())
        with db.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table} ({columns}) VALUES ({placeholders}) RETURNING *",
                params,
            )
            return cur.fetchone()

    def update(self, db, id_: Any, data: Dict[str, Any]) -> Optional[psycopg2.extras.RealDictRow]:
        params, casts = self._prepare(data)
        set_clause = ", ".join(f"{key} = %({key})s{casts[key]}" for key in data.keys())
        params["id"] = id_
        with db.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table} SET {set_clause} WHERE {self.pk_column} = %(id)s RETURNING *",
                params,
            )
            return cur.fetchone()

    def count(self, db) -> int:
        with db.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS count FROM {self.table}")
            return cur.fetchone()["count"]

    @staticmethod
    def _prepare(data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """Serialize list/dict values to JSON text and cast them ::jsonb -
        psycopg2 won't adapt Python list/dict for a jsonb column on its own."""
        params: Dict[str, Any] = {}
        casts: Dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                params[key] = json.dumps(value)
                casts[key] = "::jsonb"
            else:
                params[key] = value
                casts[key] = ""
        return params, casts
