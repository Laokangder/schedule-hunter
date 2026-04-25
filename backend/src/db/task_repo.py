from src.db.base import DBConnection
from src.core.logger import get_logger, log_with_trace
import json
from typing import List, Dict, Optional

logger = get_logger("task_repo")


class TaskRepository:
    def __init__(self):
        self.db = DBConnection()

    def create_task(self, task_data: Dict, trace_id: str):
        """创建任务"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            # 序列化JSON字段
            participants = json.dumps(task_data["participants"])
            reminder_policy = json.dumps(task_data["reminder_policy"])

            # 插入数据
            cursor.execute("""
            INSERT INTO tasks (
                task_id, title, start_time, end_time, location,
                participants, priority, reminder_policy, source_text,
                input_type, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_data["task_id"],
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

            # 解析结果
            tasks = []
            for row in rows:
                task = dict(row)
                # 反序列化JSON字段
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
