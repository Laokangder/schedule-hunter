from src.core.config import settings
from src.core.logger import get_logger, log_with_trace
from src.db.task_repo import TaskRepository
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional
import re


logger = get_logger("conflict_service")


class ConflictService:
    def __init__(self):
        self.task_repo = TaskRepository()
        self.timezone = pytz.timezone(settings.DEFAULT_TIMEZONE)

    def _parse_iso_time(self, time_str: str) -> datetime:
        return datetime.fromisoformat(time_str).astimezone(self.timezone)

    def check_time_overlap(self, candidate: Dict, existing_tasks: List[Dict], trace_id: str) -> List[Dict]:
        conflicts = []
        candidate_start = self._parse_iso_time(candidate.get("start_time"))
        candidate_end = self._parse_iso_time(candidate.get("end_time"))

        for task in existing_tasks:
            task_start = self._parse_iso_time(task["start_time"])
            task_end = self._parse_iso_time(task["end_time"])

            if (candidate_start < task_end) and (candidate_end > task_start):
                conflicts.append({
                    "task_id": task["task_id"],
                    "conflict_type": "time_overlap",
                    "conflict_level": "high" if (candidate_start >= task_start and candidate_end <= task_end) else "medium",
                    "detail": f"{candidate_start.strftime('%H:%M')}-{candidate_end.strftime('%H:%M')} 与「{task['title']}」时间重叠",
                    "suggestions": [
                        f"自动改期到 {task_end.strftime('%Y-%m-%dT%H:%M:%S%z')}",
                        "保留新任务并取消旧任务",
                        "拆分为提醒类事项"
                    ]
                })

        return conflicts

    def check_travel_conflict(self, candidate: Dict, existing_tasks: List[Dict], buffer_minutes: int, trace_id: str) -> List[Dict]:
        conflicts = []
        candidate_start = self._parse_iso_time(candidate.get("start_time"))
        buffer = timedelta(minutes=buffer_minutes)

        for task in existing_tasks:
            task_end = self._parse_iso_time(task["end_time"])
            if (candidate_start - task_end) < buffer:
                conflicts.append({
                    "task_id": task["task_id"],
                    "conflict_type": "travel_conflict",
                    "conflict_level": "medium",
                    "detail": f"任务开始时间与上一任务结束时间间隔不足{buffer_minutes}分钟，可能存在出行冲突",
                    "suggestions": [
                        f"推迟{buffer_minutes}分钟开始",
                        "调整上一任务结束时间"
                    ]
                })

        return conflicts

    def generate_suggestions(self, candidate: Dict, conflict_type: str) -> List[Dict]:
        start_time = self._parse_iso_time(candidate.get("start_time"))
        end_time = self._parse_iso_time(candidate.get("end_time"))

        if conflict_type == "time_overlap":
            reschedule_time = start_time + timedelta(hours=1.5)
            return [
                {"action": "reschedule", "suggested_time": reschedule_time.isoformat(), "description": "推迟1.5小时避免重叠"},
                {"action": "shorten", "suggested_duration_minutes": 45, "description": "压缩至45分钟，留出缓冲"},
                {"action": "dismiss", "description": "忽略此次检测，不创建任务"}
            ]
        return []

    def check_conflict(self, candidate: Dict, scope: Dict, trace_id: str) -> Dict:
        existing_tasks = self.task_repo.get_tasks_by_date(
            date=self._parse_iso_time(candidate.get("start_time")).date(),
            trace_id=trace_id
        )
        if not existing_tasks:
            return {"has_conflict": False, "conflicts": [], "ai_summary": "无冲突"}

        conflicts = []
        check_type = scope.get("check_type", "time_overlap")
        if check_type == "time_overlap":
            conflicts = self.check_time_overlap(candidate, existing_tasks, trace_id)
        elif check_type == "travel_conflict":
            conflicts = self.check_travel_conflict(
                candidate, existing_tasks, scope.get("travel_buffer_minutes", 20), trace_id
            )

        ai_summary = f"检测到{len(conflicts)}个{check_type}类型冲突，建议调整时间或时长" if conflicts else "无冲突"

        return {
            "has_conflict": len(conflicts) > 0,
            "conflicts": conflicts,
            "ai_summary": ai_summary
        }
