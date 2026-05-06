from src.db.base import DBConnection
from src.core.logger import get_logger, log_with_trace
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

logger = get_logger("task_repo")


class TaskRepository:
    def __init__(self):
        self.db = DBConnection()

    def create_task(self, task_data: Dict, trace_id: str):
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            participants = json.dumps(task_data["participants"])
            reminder_policy = json.dumps(task_data["reminder_policy"])

            cursor.execute("""
            INSERT INTO tasks (
                task_id, request_id, title, start_time, end_time, location,
                participants, priority, reminder_policy, source_text,
                input_type, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data["task_id"],
                task_data.get("request_id"),
                task_data["title"],
                task_data["start_time"],
                task_data["end_time"],
                task_data["location"],
                participants,
                task_data["priority"],
                reminder_policy,
                task_data["source_text"],
                task_data["input_type"],
                task_data["status"],
                task_data["created_at"]
            ))

            conn.commit()
            log_with_trace(logger, "INFO", f"任务写入数据库：{task_data['task_id']}", trace_id)

        except Exception as e:
            conn.rollback()
            log_with_trace(logger, "ERROR", f"任务写入失败：{str(e)}", trace_id)
            raise e

        finally:
            conn.close()

    def get_tasks_by_date(self, date: Optional[str] = None, status: Optional[str] = None, trace_id: str = "") -> List[Dict]:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            query = "SELECT * FROM tasks"
            params = []
            conditions = []

            if date:
                conditions.append("start_time LIKE ?")
                params.append(f"{date}%")

            if status:
                conditions.append("status = ?")
                params.append(status)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            tasks = []
            for row in rows:
                task = dict(row)
                task["participants"] = json.loads(task["participants"])
                task["reminder_policy"] = json.loads(task["reminder_policy"])
                tasks.append(task)

            log_with_trace(logger, "INFO", f"查询到{len(tasks)}个任务", trace_id)
            return tasks

        except Exception as e:
            log_with_trace(logger, "ERROR", f"查询任务失败：{str(e)}", trace_id)
            return []

        finally:
            conn.close()

    def get_task_by_request_id(self, request_id: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM tasks WHERE request_id = ?", (request_id,))
            row = cursor.fetchone()
            if row:
                task = dict(row)
                task["participants"] = json.loads(task["participants"])
                task["reminder_policy"] = json.loads(task["reminder_policy"])
                return task
            return None
        finally:
            conn.close()

    def get_pending_reminders(self, minutes_threshold: int = 30) -> List[Dict]:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.now(timezone(timedelta(hours=8)))
            future_time = now + timedelta(minutes=minutes_threshold)

            cursor.execute("""
                SELECT * FROM tasks
                WHERE status = 'scheduled'
                AND is_reminded = 0
                AND start_time > ?
                AND start_time <= ?
            """, (now.isoformat(), future_time.isoformat()))

            rows = cursor.fetchall()
            tasks = []
            for row in rows:
                task = dict(row)
                task["participants"] = json.loads(task["participants"])
                task["reminder_policy"] = json.loads(task["reminder_policy"])
                tasks.append(task)

            log_with_trace(logger, "INFO", f"待提醒任务：{len(tasks)}个", "")
            return tasks

        except Exception as e:
            log_with_trace(logger, "ERROR", f"查询待提醒任务失败：{str(e)}", "")
            return []

        finally:
            conn.close()

    def mark_reminded(self, task_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tasks SET is_reminded = 1 WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log_with_trace(logger, "ERROR", f"标记已提醒失败：{str(e)}", "")
            return False
        finally:
            conn.close()

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE tasks SET status = ? WHERE task_id = ?", (new_status, task_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            log_with_trace(logger, "ERROR", f"更新任务状态失败：{str(e)}", "")
            return False
        finally:
            conn.close()

    def expire_overdue_tasks(self) -> int:
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT task_id, end_time FROM tasks WHERE status = 'pending'")
            rows = cursor.fetchall()

            tz = timezone(timedelta(hours=8))
            now = datetime.now(tz)
            expired_ids = []

            for row in rows:
                try:
                    end_time_str = row["end_time"]
                    end_dt = datetime.fromisoformat(end_time_str)
                    if end_dt.tzinfo is None:
                        end_dt = end_dt.replace(tzinfo=tz)
                    if end_dt < now:
                        expired_ids.append(row["task_id"])
                except Exception:
                    continue

            if expired_ids:
                placeholders = ','.join('?' * len(expired_ids))
                cursor.execute(f"UPDATE tasks SET status = 'expired' WHERE task_id IN ({placeholders})", expired_ids)
                conn.commit()
                log_with_trace(logger, "INFO", f"过期任务数量：{len(expired_ids)}", "")
                return len(expired_ids)
            return 0
        except Exception as e:
            log_with_trace(logger, "ERROR", f"过期判定失败：{str(e)}", "")
            return 0
        finally:
            conn.close()

    def delete_task(self, task_id: str, trace_id: str) -> bool:
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
            if not cursor.fetchone():
                log_with_trace(logger, "WARNING", f"任务不存在：{task_id}", trace_id)
                return False

            cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()

            if cursor.rowcount > 0:
                log_with_trace(logger, "INFO", f"任务已删除：{task_id}", trace_id)
                return True
            return False

        except Exception as e:
            conn.rollback()
            log_with_trace(logger, "ERROR", f"删除任务失败：{str(e)}", trace_id)
            return False

        finally:
            conn.close()
