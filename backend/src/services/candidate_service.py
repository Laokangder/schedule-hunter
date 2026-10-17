import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from src.db.candidate_repo import CandidateRepository
from src.db.idempotency_repo import IdempotencyRepository
from src.models.request import CandidateCreateRequest, CandidateSnoozeRequest, CandidateUpdateRequest
from src.services.change_hunter_service import ChangeHunterService


class CandidateService:
    def __init__(self):
        self.repo = CandidateRepository()
        self.idempotency = IdempotencyRepository()
        self.change_hunter = ChangeHunterService()

    @staticmethod
    def _normalize(value: Optional[str]) -> str:
        return re.sub(r"\s+", "", (value or "").strip().lower())

    @classmethod
    def _dedup_key(cls, source_text: str) -> str:
        return hashlib.sha256(cls._normalize(source_text).encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_time(value: Optional[str]):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None
            if parsed and parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (TypeError, ValueError):
            return None

    @classmethod
    def _similar(cls, first: Dict, second: Dict) -> bool:
        first_parsed = first.get("parsed") or {}
        second_parsed = second.get("parsed") or {}
        title = cls._normalize(first_parsed.get("title"))
        if not title or title != cls._normalize(second_parsed.get("title")):
            return False
        first_start = cls._parse_time(first_parsed.get("start_time"))
        second_start = cls._parse_time(second_parsed.get("start_time"))
        if not first_start or not second_start or abs((first_start - second_start).total_seconds()) > 600:
            return False
        first_location = cls._normalize(first_parsed.get("location"))
        second_location = cls._normalize(second_parsed.get("location"))
        return not first_location or not second_location or first_location == second_location

    @staticmethod
    def _source_summary(request: CandidateCreateRequest, now: str) -> Dict:
        return {
            "source_type": request.source_type,
            "source_package": request.source_package,
            "source_app_name": request.source_app_name,
            "received_at": now,
        }

    def create_or_merge(self, request: CandidateCreateRequest) -> Dict:
        existing_request = self.repo.get_by_request_id(request.request_id)
        if existing_request:
            return {"candidate": existing_request, "idempotent": True, "merged": False}

        now = datetime.now(timezone.utc).isoformat()
        analysis = self.change_hunter.analyze(
            request.source_text,
            request.parsed,
            request.intent_type,
            request.target_task_id,
            request.changes,
            request.match_confidence,
        )
        incoming = {
            "candidate_id": f"cand_{uuid.uuid4().hex[:10]}",
            "request_id": request.request_id,
            "dedup_key": self._dedup_key(request.source_text),
            "intent_type": analysis["intent_type"],
            "target_task_id": analysis["target_task_id"],
            "source_type": request.source_type,
            "source_package": request.source_package,
            "source_app_name": request.source_app_name,
            "source_text": request.source_text,
            "parsed": request.parsed,
            "changes": analysis["changes"],
            "confidence": request.confidence,
            "match_confidence": analysis["match_confidence"],
            "status": "pending",
            "seen_count": 1,
            "sources": [self._source_summary(request, now)],
            "created_at": now,
            "updated_at": now,
        }

        exact = self.repo.get_by_dedup_key(incoming["dedup_key"])
        if exact:
            merged = self.repo.merge(
                exact["candidate_id"], incoming, request.confidence > float(exact.get("confidence") or 0)
            )
            return {"candidate": merged, "idempotent": False, "merged": True}

        for candidate in self.repo.get_mergeable(incoming["intent_type"]):
            if self._similar(candidate, incoming):
                merged = self.repo.merge(
                    candidate["candidate_id"], incoming,
                    request.confidence > float(candidate.get("confidence") or 0),
                )
                return {"candidate": merged, "idempotent": False, "merged": True}

        return {"candidate": self.repo.create(incoming), "idempotent": False, "merged": False}

    def list(self, status: Optional[str] = None, due: bool = False, now: Optional[str] = None) -> List[Dict]:
        if due:
            due_at = self._parse_time(now) if now else datetime.now(timezone.utc)
            if due_at is None:
                raise ValueError("时间非法（错误码2001）")
            return self.repo.get_due_snoozed(due_at.isoformat())
        return self.repo.list(status)

    def get(self, candidate_id: str) -> Optional[Dict]:
        return self.repo.get_by_id(candidate_id)

    def update(self, candidate_id: str, request: CandidateUpdateRequest) -> Optional[Dict]:
        operation = f"candidate.update:{candidate_id}"
        cached = self.idempotency.get(request.request_id, operation)
        if cached is not None:
            return cached
        updates = request.model_dump(exclude_none=True, exclude={"request_id"})
        updated = self.repo.update(candidate_id, updates)
        if updated:
            self.idempotency.save(request.request_id, operation, updated)
        return updated

    def snooze(self, candidate_id: str, request: CandidateSnoozeRequest) -> Optional[Dict]:
        operation = f"candidate.snooze:{candidate_id}"
        cached = self.idempotency.get(request.request_id, operation)
        if cached is not None:
            return cached
        if request.snoozed_until:
            try:
                until = datetime.fromisoformat(request.snoozed_until.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("时间非法（错误码2001）") from exc
            if until.tzinfo is None:
                until = until.replace(tzinfo=timezone.utc)
        elif request.duration_minutes in (10, 60):
            until = datetime.now(timezone.utc) + timedelta(minutes=request.duration_minutes)
        else:
            raise ValueError("时间非法（错误码2001）")
        updated = self.repo.update(candidate_id, {
            "status": "snoozed",
            "snoozed_until": until.isoformat(),
            "snooze_notified_at": None,
        })
        if updated:
            self.idempotency.save(request.request_id, operation, updated)
        return updated

    def confirm(self, candidate_id: str, request_id: str) -> Optional[Dict]:
        return self.repo.confirm(candidate_id, request_id)
