import json
from datetime import datetime, timezone
from typing import Dict, Optional

from src.db.base import DBConnection


class IdempotencyRepository:
    def __init__(self):
        self.db = DBConnection()

    def get(self, request_id: str, operation: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                "SELECT response_data FROM idempotency_operations WHERE request_id = ? AND operation = ?",
                (request_id, operation),
            ).fetchone()
            return json.loads(row["response_data"]) if row else None
        finally:
            conn.close()

    def save(self, request_id: str, operation: str, response_data: Dict) -> None:
        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO idempotency_operations
                    (request_id, operation, response_data, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    request_id,
                    operation,
                    json.dumps(response_data, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
