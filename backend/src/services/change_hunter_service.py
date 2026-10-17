import re
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from src.db.task_repo import TaskRepository


class ChangeHunterService:
    def __init__(self):
        self.task_repo = TaskRepository()

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        return re.sub(r"\s+", "", (value or "").strip().lower())

    @staticmethod
    def _parse_time(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return None

    def _match_task(self, source_text: str, parsed: Dict) -> Tuple[Optional[str], float]:
        active = [
            task for task in self.task_repo.get_all_tasks()
            if task.get("status") not in {"completed", "expired", "cancelled"}
        ]
        if not active:
            return None, 0.0

        source_norm = self._normalize(source_text)
        title_norm = self._normalize(parsed.get("title"))
        parsed_start = self._parse_time(parsed.get("start_time"))
        parsed_location = self._normalize(parsed.get("location"))
        parsed_participants = set(parsed.get("participants") or [])
        best_task = None
        best_score = 0.0

        for task in active:
            score = 0.0
            task_title = self._normalize(task.get("title"))
            if title_norm and task_title:
                if title_norm == task_title:
                    score += 0.55
                elif title_norm in task_title or task_title in title_norm:
                    score += 0.4
            if task_title and task_title in source_norm:
                score = max(score, 0.5)

            task_start = self._parse_time(task.get("start_time"))
            if parsed_start and task_start:
                seconds = abs((parsed_start - task_start).total_seconds())
                if seconds <= 600:
                    score += 0.25
                elif parsed_start.date() == task_start.date():
                    score += 0.1

            task_location = self._normalize(task.get("location"))
            if parsed_location and task_location and parsed_location == task_location:
                score += 0.15

            task_participants = set(task.get("participants") or [])
            if parsed_participants and task_participants:
                overlap = len(parsed_participants & task_participants)
                score += min(0.1, overlap / max(len(parsed_participants), 1) * 0.1)

            if score > best_score:
                best_score = score
                best_task = task

        if best_score < 0.4 and len(active) == 1:
            best_task = active[0]
            best_score = 0.4
        return (best_task.get("task_id"), min(best_score, 1.0)) if best_task else (None, 0.0)

    def analyze(
        self,
        source_text: str,
        parsed: Optional[Dict] = None,
        intent_type: Optional[str] = None,
        target_task_id: Optional[str] = None,
        changes: Optional[Dict] = None,
        match_confidence: float = 0.0,
    ) -> Dict:
        parsed = dict(parsed or {})
        detected_intent = intent_type
        if not detected_intent:
            if re.search(r"取消|不用开|不开了|作废", source_text):
                detected_intent = "cancel"
            elif re.search(r"推迟|提前|改到|改为|换到|地点改|时间改", source_text):
                detected_intent = "update"
            else:
                detected_intent = "create"

        detected_changes = dict(changes or {})
        if detected_intent == "update":
            location_match = re.search(r"(?:地点)?(?:改到|改为|换到)\s*([^，,。.!！？]+)", source_text)
            has_time_change = bool(re.search(r"(?:推迟|提前|时间改|改到).*?(?:点|时|:\d{1,2})", source_text))
            if location_match and not has_time_change:
                detected_changes.setdefault("location", location_match.group(1).strip())
            if has_time_change and parsed.get("start_time"):
                detected_changes.setdefault("start_time", parsed["start_time"])
                if parsed.get("end_time"):
                    detected_changes.setdefault("end_time", parsed["end_time"])

        matched_target = target_task_id
        matched_confidence = match_confidence
        if detected_intent in {"update", "cancel"} and not matched_target:
            matched_target, matched_confidence = self._match_task(source_text, parsed)

        return {
            "intent_type": detected_intent,
            "target_task_id": matched_target,
            "changes": detected_changes,
            "match_confidence": matched_confidence,
        }
