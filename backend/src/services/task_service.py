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
        """创建任务"""
        try:
            # 生成任务ID
            task_id = f"task_{uuid.uuid4().hex[:6]}"

            # 构建任务数据
            task_data = {
                "task_id": task_id,
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

            # 写入数据库
            self.task_repo.create_task(task_data, trace_id)
            log_with_trace(logger, "INFO", f"任务创建成功：{task_id}", trace_id)

            return {
                "task_id": task_id,
                "status": "scheduled",
                "normalized": {
                    "start_time": request.parsed.start_time,
                    "end_time": request.parsed.end_time
                },
                "is_conflict": False
            }

        except Exception as e:
            log_with_trace(logger, "ERROR", f"任务创建失败：{str(e)}", trace_id)
            raise ValueError("任务写入失败（错误码3001）")

    def get_tasks_by_date(self, date: str, status: Optional[str], trace_id: str) -> Dict:
        """按日期查询任务"""
        try:
            tasks = self.task_repo.get_tasks_by_date(date, status, trace_id)

            # 计算灵动岛状态
            island_state = self._get_island_state(tasks)

            return {
                "task_list": tasks,
                "island_state": island_state
            }
        except Exception as e:
            log_with_trace(logger, "ERROR", f"查询任务失败：{str(e)}", trace_id)
            raise ValueError("任务查询失败")

    def _get_island_state(self, tasks: List[Dict]) -> Dict:
        """计算灵动岛状态（简化版）"""
        if not tasks:
            return {"mode": "silent", "display_text": "", "severity": "info"}

        # 实际需根据任务时间计算状态，此处简化
        return {
            "mode": "countdown",
            "display_text": "还有2h 32m",
            "severity": "info"
        }
