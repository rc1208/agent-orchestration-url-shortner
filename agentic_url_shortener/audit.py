import json
from datetime import UTC, datetime

from .database import Database


class AuditRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def record(self, run_id: str, event_type: str, *, node: str | None = None,
               actor: str = "system", revision: int = 1, rationale: str = "",
               data: dict | None = None) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "INSERT INTO audit_events(run_id, correlation_id, event_type, node, actor, "
                "requirement_revision, rationale, data_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, run_id, event_type, node, actor, revision, rationale,
                 json.dumps(data or {}, default=str), datetime.now(UTC).isoformat()),
            )

    def list(self, run_id: str) -> list[dict]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events WHERE run_id = ? ORDER BY event_id", (run_id,)
            ).fetchall()
        return [{**dict(row), "data": json.loads(row["data_json"])} for row in rows]
