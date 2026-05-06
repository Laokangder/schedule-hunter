from src.db.task_repo import TaskRepository
from src.models.request import CreateTaskRequest
from src.core.logger import get_logger, log_with_trace
from typing import List, Dict, Optional
import uuid

logger = get_logger("task_service")


class TaskService:
    def __init__(self):
        self.task_repo = TaskRepository()

    def create_task(self, request: CreateTaskRequest, trace_id: str) -> Dict:
        request_id = getattr(request, 'request_id', None)
        if request_id:
            existing = self.task_repo.get_task_by_request_id(request_id)
            if existing:
                log_with_trace(logger, "INFO", f"幂等返回：request_id={request_id}", trace_id)
                return {
                    "task_id": existing["task_id"],
                    "status": existing["status"],
                    "normalized": {
                        "start_time": existing["start_time"],
                        "end_time": existing["end_time"]
                    },
                    "is_conflict": False,
                    "idempotent": True
                }

        try:
            task_id = f"task_{uuid.uuid4().hex[:6]}"

            task_data = {
                "task_id": task_id,
                "request_id": request_id,
                "title": request.parsed.title,
                "start_time": request.parsed.start_time,
                "end_time": request.parsed.end_time,
                "location": request.parsed.location,
                "participants": request.parsed.participants,
                "priority": request.priority,
                "reminder_policy": request.reminder_policy.model_dump(),
                "source_text": request.source_text,
                "input_type": request.meta.input_type,
                "status": "scheduled",
                "created_at": request.meta.client_timestamp
            }

            self.task_repo.create_task(task_data, trace_id)
            log_with_trace(logger, "INFO", f"任务创建成功：{task_id}", trace_id)

            return {
                "task_id": task_id,
                "status": "scheduled",
                "normalized": {
                    "start_time": request.parsed.start_time,
                    "end_time": request.parsed.end_time
                },
                "is_conflict": False,
                "idempotent": False
            }

        except Exception as e:
            log_with_trace(logger, "ERROR", f"任务创建失败：{str(e)}", trace_id)
            raise ValueError("任务写入失败（错误码3001）")

    def get_tasks_by_date(self, date: str, status: Optional[str], trace_id: str) -> Dict:
        try:
            tasks = self.task_repo.get_tasks_by_date(date, status, trace_id)

            island_state = self._get_island_state(tasks)

            return {
                "task_list": tasks,
                "island_state": island_state
            }
        except Exception as e:
            log_with_trace(logger, "ERROR", f"查询任务失败：{str(e)}", trace_id)
            raise ValueError("任务查询失败")

    def _get_island_state(self, tasks: List[Dict]) -> Dict:
        if not tasks:
            return {"mode": "silent", "display_text": "", "severity": "info"}

        return {
            "mode": "countdown",
            "display_text": "还有2h 32m",
            "severity": "info"
        }

    def delete_task(self, task_id: str, trace_id: str) -> bool:
        try:
            return self.task_repo.delete_task(task_id, trace_id)
        except Exception as e:
            log_with_trace(logger, "ERROR", f"删除任务失败：{str(e)}", trace_id)
            return False

    def get_pending_reminders(self) -> List[Dict]:
        return self.task_repo.get_pending_reminders(30)

    def mark_reminded(self, task_id: str) -> bool:
        return self.task_repo.mark_reminded(task_id)

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        return self.task_repo.update_task_status(task_id, new_status)

    def expire_overdue_tasks(self) -> int:
        return self.task_repo.expire_overdue_tasks()
