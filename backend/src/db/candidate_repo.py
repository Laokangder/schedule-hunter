import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from src.db.base import DBConnection


JSON_FIELDS = {"parsed", "changes", "sources"}


class CandidateRepository:
    def __init__(self):
        self.db = DBConnection()

    @staticmethod
    def deserialize(row) -> Optional[Dict]:
        if not row:
            return None
        candidate = dict(row)
        for field in JSON_FIELDS:
            default = "[]" if field == "sources" else "{}"
            candidate[field] = json.loads(candidate.get(field) or default)
        return candidate

    def get_by_request_id(self, request_id: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                """SELECT candidates.* FROM candidates
                   LEFT JOIN candidate_requests
                     ON candidate_requests.candidate_id = candidates.candidate_id
                   WHERE candidates.request_id = ? OR candidate_requests.request_id = ?
                   LIMIT 1""",
                (request_id, request_id),
            ).fetchone()
            return self.deserialize(row)
        finally:
            conn.close()

    def get_by_id(self, candidate_id: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            return self.deserialize(row)
        finally:
            conn.close()

    def get_by_dedup_key(self, dedup_key: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            row = conn.execute(
                """SELECT candidates.* FROM candidates
                   LEFT JOIN candidate_dedup_keys
                     ON candidate_dedup_keys.candidate_id = candidates.candidate_id
                   WHERE candidates.dedup_key = ? OR candidate_dedup_keys.dedup_key = ?
                   ORDER BY candidates.updated_at DESC LIMIT 1""",
                (dedup_key, dedup_key),
            ).fetchone()
            return self.deserialize(row)
        finally:
            conn.close()

    def get_mergeable(self, intent_type: str) -> List[Dict]:
        conn = self.db.get_connection()
        try:
            rows = conn.execute(
                """SELECT * FROM candidates
                   WHERE status IN ('pending', 'snoozed') AND intent_type = ?
                   ORDER BY updated_at DESC""",
                (intent_type,),
            ).fetchall()
            return [self.deserialize(row) for row in rows]
        finally:
            conn.close()

    def create(self, data: Dict) -> Dict:
        conn = self.db.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO candidates (
                    candidate_id, request_id, dedup_key, intent_type, target_task_id,
                    source_type, source_package, source_app_name, source_text, parsed,
                    changes, confidence, match_confidence, status, snoozed_until,
                    snooze_notified_at, seen_count, sources, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["candidate_id"], data["request_id"], data["dedup_key"], data["intent_type"],
                    data.get("target_task_id"), data["source_type"], data.get("source_package"),
                    data.get("source_app_name"), data["source_text"],
                    json.dumps(data.get("parsed", {}), ensure_ascii=False),
                    json.dumps(data.get("changes", {}), ensure_ascii=False), data.get("confidence", 0),
                    data.get("match_confidence", 0), data.get("status", "pending"),
                    data.get("snoozed_until"), data.get("snooze_notified_at"), data.get("seen_count", 1),
                    json.dumps(data.get("sources", []), ensure_ascii=False), data["created_at"], data["updated_at"],
                ),
            )
            conn.execute(
                "INSERT OR IGNORE INTO candidate_requests (request_id, candidate_id, created_at) VALUES (?, ?, ?)",
                (data["request_id"], data["candidate_id"], data["created_at"]),
            )
            conn.execute(
                "INSERT OR IGNORE INTO candidate_dedup_keys (dedup_key, candidate_id, created_at) VALUES (?, ?, ?)",
                (data["dedup_key"], data["candidate_id"], data["created_at"]),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (data["candidate_id"],)).fetchone()
            return self.deserialize(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def merge(self, candidate_id: str, incoming: Dict, replace_main: bool) -> Dict:
        conn = self.db.get_connection()
        try:
            current = self.deserialize(
                conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            )
            sources = current["sources"]
            source = incoming["sources"][0]
            if source not in sources:
                sources.append(source)
            updates = {
                "seen_count": current["seen_count"] + 1,
                "sources": json.dumps(sources, ensure_ascii=False),
                "updated_at": incoming["updated_at"],
            }
            if replace_main:
                updates.update({
                    "parsed": json.dumps(incoming.get("parsed", {}), ensure_ascii=False),
                    "changes": json.dumps(incoming.get("changes", {}), ensure_ascii=False),
                    "confidence": incoming.get("confidence", 0),
                    "match_confidence": incoming.get("match_confidence", 0),
                    "target_task_id": incoming.get("target_task_id"),
                    "source_type": incoming.get("source_type"),
                    "source_package": incoming.get("source_package"),
                    "source_app_name": incoming.get("source_app_name"),
                    "source_text": incoming.get("source_text"),
                })
            assignments = ", ".join(f"{key} = ?" for key in updates)
            conn.execute(
                f"UPDATE candidates SET {assignments} WHERE candidate_id = ?",
                list(updates.values()) + [candidate_id],
            )
            conn.execute(
                "INSERT OR IGNORE INTO candidate_requests (request_id, candidate_id, created_at) VALUES (?, ?, ?)",
                (incoming["request_id"], candidate_id, incoming["updated_at"]),
            )
            conn.execute(
                "INSERT OR IGNORE INTO candidate_dedup_keys (dedup_key, candidate_id, created_at) VALUES (?, ?, ?)",
                (incoming["dedup_key"], candidate_id, incoming["updated_at"]),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            return self.deserialize(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def list(self, status: Optional[str] = None) -> List[Dict]:
        conn = self.db.get_connection()
        try:
            if status:
                rows = conn.execute(
                    "SELECT * FROM candidates WHERE status = ? ORDER BY updated_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM candidates ORDER BY updated_at DESC").fetchall()
            return [self.deserialize(row) for row in rows]
        finally:
            conn.close()

    def get_due_snoozed(self, now_iso: str) -> List[Dict]:
        conn = self.db.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """SELECT * FROM candidates
                   WHERE status = 'snoozed' AND snoozed_until <= ?
                     AND snooze_notified_at IS NULL
                   ORDER BY snoozed_until ASC""",
                (now_iso,),
            ).fetchall()
            ids = [row["candidate_id"] for row in rows]
            if ids:
                placeholders = ",".join("?" for _ in ids)
                conn.execute(
                    f"UPDATE candidates SET snooze_notified_at = ?, updated_at = ? WHERE candidate_id IN ({placeholders})",
                    [now_iso, now_iso, *ids],
                )
                rows = conn.execute(
                    f"SELECT * FROM candidates WHERE candidate_id IN ({placeholders}) ORDER BY snoozed_until ASC",
                    ids,
                ).fetchall()
            conn.commit()
            return [self.deserialize(row) for row in rows]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def update(self, candidate_id: str, updates: Dict) -> Optional[Dict]:
        allowed = {
            "parsed", "changes", "confidence", "status", "target_task_id",
            "snoozed_until", "snooze_notified_at",
        }
        values = {key: value for key, value in updates.items() if key in allowed}
        for field in ("parsed", "changes"):
            if field in values:
                values[field] = json.dumps(values[field], ensure_ascii=False)
        values["updated_at"] = datetime.now(timezone.utc).isoformat()
        conn = self.db.get_connection()
        try:
            if not conn.execute("SELECT 1 FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone():
                return None
            assignments = ", ".join(f"{key} = ?" for key in values)
            conn.execute(
                f"UPDATE candidates SET {assignments} WHERE candidate_id = ?",
                list(values.values()) + [candidate_id],
            )
            conn.commit()
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            return self.deserialize(row)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def confirm(self, candidate_id: str, request_id: str) -> Optional[Dict]:
        operation = f"candidate.confirm:{candidate_id}"
        conn = self.db.get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cached = conn.execute(
                "SELECT response_data FROM idempotency_operations WHERE request_id = ? AND operation = ?",
                (request_id, operation),
            ).fetchone()
            if cached:
                result = json.loads(cached["response_data"])
                result["idempotent"] = True
                conn.commit()
                return result

            candidate = self.deserialize(
                conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            )
            if not candidate:
                conn.rollback()
                return None
            if candidate["status"] == "confirmed":
                task = self._load_task(conn, candidate.get("target_task_id"))
                conn.commit()
                return {"candidate": candidate, "task": task, "idempotent": True}
            if candidate["status"] == "ignored":
                raise ValueError("已忽略候选不能确认")

            now = datetime.now(timezone.utc).isoformat()
            target_task_id = candidate.get("target_task_id")
            if candidate["intent_type"] == "create":
                target_task_id = self._create_task(conn, candidate, request_id, now)
            elif candidate["intent_type"] == "cancel":
                self._require_task(conn, target_task_id)
                conn.execute(
                    "UPDATE tasks SET status = 'cancelled', updated_at = ? WHERE task_id = ?",
                    (now, target_task_id),
                )
            else:
                self._update_task(conn, target_task_id, candidate["changes"], now)

            conn.execute(
                """UPDATE candidates
                   SET status = 'confirmed', target_task_id = ?, snoozed_until = NULL,
                       snooze_notified_at = NULL, updated_at = ?
                   WHERE candidate_id = ?""",
                (target_task_id, now, candidate_id),
            )
            updated_candidate = self.deserialize(
                conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
            )
            result = {
                "candidate": updated_candidate,
                "task": self._load_task(conn, target_task_id),
                "idempotent": False,
            }
            conn.execute(
                "INSERT INTO idempotency_operations (request_id, operation, response_data, created_at) VALUES (?, ?, ?, ?)",
                (request_id, operation, json.dumps(result, ensure_ascii=False), now),
            )
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _load_task(conn, task_id: Optional[str]) -> Optional[Dict]:
        if not task_id:
            return None
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            return None
        task = dict(row)
        task["participants"] = json.loads(task.get("participants") or "[]")
        task["reminder_policy"] = json.loads(task.get("reminder_policy") or "{}")
        return task

    @staticmethod
    def _require_task(conn, task_id: Optional[str]):
        if not task_id:
            raise ValueError("任务不存在（错误码4001）")
        row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError("任务不存在（错误码4001）")
        return row

    def _create_task(self, conn, candidate: Dict, request_id: str, now: str) -> str:
        parsed = candidate["parsed"]
        start_time = parsed.get("start_time")
        end_time = parsed.get("end_time")
        self._validate_times(start_time, end_time)
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO tasks (
                   task_id, request_id, title, start_time, end_time, location,
                   participants, priority, reminder_policy, source_text,
                   input_type, status, is_reminded, reminded_offsets, created_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', 0, '[]', ?, ?)""",
            (
                task_id, request_id, parsed.get("title") or "未命名日程", start_time, end_time,
                parsed.get("location"), json.dumps(parsed.get("participants") or [], ensure_ascii=False),
                parsed.get("priority", "normal"),
                json.dumps(
                    parsed.get("reminder_policy") or {"enabled": True, "offset_minutes": [30, 10, 5]},
                    ensure_ascii=False,
                ),
                candidate["source_text"], candidate["source_type"], now, now,
            ),
        )
        return task_id

    def _update_task(self, conn, task_id: Optional[str], changes: Dict, now: str) -> None:
        row = self._require_task(conn, task_id)
        allowed = {"title", "start_time", "end_time", "location", "participants", "priority", "reminder_policy"}
        values = {}
        for key, raw_value in changes.items():
            if key in allowed:
                values[key] = raw_value.get("to") if isinstance(raw_value, dict) and "to" in raw_value else raw_value
        start_time = values.get("start_time", row["start_time"])
        end_time = values.get("end_time", row["end_time"])
        self._validate_times(start_time, end_time)
        for field in ("participants", "reminder_policy"):
            if field in values:
                values[field] = json.dumps(values[field], ensure_ascii=False)
        if any(key in values for key in ("start_time", "end_time", "reminder_policy")):
            values["reminded_offsets"] = "[]"
            values["is_reminded"] = 0
        values["updated_at"] = now
        if values:
            assignments = ", ".join(f"{key} = ?" for key in values)
            conn.execute(f"UPDATE tasks SET {assignments} WHERE task_id = ?", list(values.values()) + [task_id])

    @staticmethod
    def _validate_times(start_time: Optional[str], end_time: Optional[str]) -> None:
        try:
            start = datetime.fromisoformat((start_time or "").replace("Z", "+00:00"))
            end = datetime.fromisoformat((end_time or "").replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError) as exc:
            raise ValueError("时间非法（错误码2001）") from exc
        if end <= start:
            raise ValueError("时间非法（错误码2001）")
