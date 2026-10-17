from src.db.task_repo import TaskRepository
from src.models.request import CreateTaskRequest, UpdateTaskRequest
from src.db.idempotency_repo import IdempotencyRepository
from src.core.logger import get_logger, log_with_trace
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone

logger = get_logger("task_service")


class TaskService:
    def __init__(self):
        self.task_repo = TaskRepository()
        self.idempotency_repo = IdempotencyRepository()

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
            if self._parse_datetime(request.parsed.end_time) <= self._parse_datetime(request.parsed.start_time):
                raise ValueError("时间非法（错误码2001）")
        except (TypeError, ValueError) as exc:
            if "2001" in str(exc):
                raise
            raise ValueError("时间非法（错误码2001）") from exc

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

    def get_tasks_by_date(self, date: Optional[str], status: Optional[str], trace_id: str) -> Dict:
        try:
            self.task_repo.expire_overdue_tasks()
            tasks = self.task_repo.get_tasks_by_date(date, status, trace_id)

            island_state = self._get_island_state(tasks)

            return {
                "task_list": tasks,
                "island_state": island_state
            }
        except Exception as e:
            log_with_trace(logger, "ERROR", f"查询任务失败：{str(e)}", trace_id)
            raise ValueError("任务查询失败")

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self.task_repo.get_task_by_id(task_id)

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

    def update_task(self, task_id: str, request: UpdateTaskRequest, trace_id: str) -> Optional[Dict]:
        operation = f"task.update:{task_id}"
        cached = self.idempotency_repo.get(request.request_id, operation)
        if cached is not None:
            result = dict(cached)
            result["idempotent"] = True
            return result

        existing = self.task_repo.get_task_by_id(task_id)
        if not existing:
            return None

        updates = request.model_dump(exclude_none=True, exclude={"request_id"})
        if "reminder_policy" in updates and hasattr(updates["reminder_policy"], "model_dump"):
            updates["reminder_policy"] = updates["reminder_policy"].model_dump()

        start_time = updates.get("start_time", existing["start_time"])
        end_time = updates.get("end_time", existing["end_time"])
        try:
            if self._parse_datetime(end_time) <= self._parse_datetime(start_time):
                raise ValueError("时间非法（错误码2001）")
        except (TypeError, ValueError) as exc:
            if "2001" in str(exc):
                raise
            raise ValueError("时间非法（错误码2001）") from exc

        reset_reminders = any(
            key in updates and updates[key] != existing.get(key)
            for key in ("start_time", "end_time", "reminder_policy")
        )
        updated = self.task_repo.update_task(task_id, updates, reset_reminders=reset_reminders)
        if updated is not None:
            updated = {**updated, "idempotent": False}
            self.idempotency_repo.save(request.request_id, operation, updated)
            log_with_trace(logger, "INFO", f"任务更新成功：{task_id}", trace_id)
        return updated

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

    def mark_reminded(self, task_id: str, offset_minutes: int) -> bool:
        return self.task_repo.mark_reminded(task_id, offset_minutes)

    def update_task_status(self, task_id: str, new_status: str) -> bool:
        return self.task_repo.update_task_status(task_id, new_status)

    def expire_overdue_tasks(self) -> int:
        return self.task_repo.expire_overdue_tasks()

    def delete_expired_tasks(self, trace_id: str) -> int:
        self.task_repo.expire_overdue_tasks()
        return self.task_repo.delete_expired_tasks(trace_id)
