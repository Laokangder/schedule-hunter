from datetime import datetime, time, timedelta, timezone
from typing import Dict

from src.db.task_repo import TaskRepository
from src.models.request import FreeSlotsRequest


class FreeSlotService:
    def __init__(self):
        self.task_repo = TaskRepository()

    @staticmethod
    def _dt(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("时间非法（错误码2001）") from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _clock(value: str) -> time:
        try:
            return time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("时间非法（错误码2001）") from exc

    def scan(self, request: FreeSlotsRequest) -> Dict:
        range_start = self._dt(request.range_start)
        range_end = self._dt(request.range_end)
        if range_end <= range_start:
            raise ValueError("时间非法（错误码2001）")
        preferred = self._dt(request.preferred_start) if request.preferred_start else None
        work_start = self._clock(request.working_hours.start)
        work_end = self._clock(request.working_hours.end)
        if work_end <= work_start:
            raise ValueError("时间非法（错误码2001）")

        buffer_delta = timedelta(minutes=request.buffer_minutes)
        occupied = []
        for task in self.task_repo.get_all_tasks():
            if task.get("status") in {"completed", "expired", "cancelled"}:
                continue
            try:
                start = self._dt(task["start_time"]) - buffer_delta
                end = self._dt(task["end_time"]) + buffer_delta
            except (KeyError, ValueError):
                continue
            if end > range_start and start < range_end:
                occupied.append((max(start, range_start), min(end, range_end)))
        occupied.sort(key=lambda item: item[0])
        merged = []
        for interval in occupied:
            if not merged or interval[0] > merged[-1][1]:
                merged.append([interval[0], interval[1]])
            else:
                merged[-1][1] = max(merged[-1][1], interval[1])

        duration = timedelta(minutes=request.duration_minutes)
        gaps = []
        current_date = range_start.date()
        while current_date <= range_end.date():
            day_start = datetime.combine(current_date, work_start, tzinfo=range_start.tzinfo)
            day_end = datetime.combine(current_date, work_end, tzinfo=range_start.tzinfo)
            window_start = max(day_start, range_start)
            window_end = min(day_end, range_end)
            if window_end > window_start:
                cursor = window_start
                for busy_start, busy_end in merged:
                    if busy_end <= window_start or busy_start >= window_end:
                        continue
                    if busy_start - cursor >= duration:
                        gaps.append((cursor, min(busy_start, window_end)))
                    cursor = max(cursor, busy_end)
                    if cursor >= window_end:
                        break
                if window_end - cursor >= duration:
                    gaps.append((cursor, window_end))
            current_date += timedelta(days=1)

        candidates = []
        for gap_start, gap_end in gaps:
            starts = [gap_start]
            if preferred and gap_start <= preferred and preferred + duration <= gap_end:
                starts.append(preferred)
            latest = gap_end - duration
            if latest > gap_start:
                starts.append(latest)
            for start in starts:
                item = (start, start + duration, gap_end - gap_start)
                if item not in candidates:
                    candidates.append(item)

        if not candidates:
            return {"suggestions": []}
        earliest = min(candidates, key=lambda item: item[0])
        closest = min(candidates, key=lambda item: abs((item[0] - preferred).total_seconds())) if preferred else earliest
        least_impact = max(candidates, key=lambda item: (item[2], -item[0].timestamp()))
        ranked = [(earliest, "最早可用"), (closest, "最接近原时间"), (least_impact, "当天影响最小")]
        suggestions = []
        seen = set()
        for item, reason in ranked:
            key = (item[0], item[1])
            if key not in seen:
                seen.add(key)
                suggestions.append({"start_time": item[0].isoformat(), "end_time": item[1].isoformat(), "reason": reason})
        if len(suggestions) < 3:
            for item in sorted(candidates, key=lambda value: value[0]):
                key = (item[0], item[1])
                if key in seen:
                    continue
                seen.add(key)
                suggestions.append({"start_time": item[0].isoformat(), "end_time": item[1].isoformat(), "reason": "可用空档"})
                if len(suggestions) == 3:
                    break
        return {"suggestions": suggestions}
