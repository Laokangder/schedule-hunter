from src.services.llm_service import BlueLMService
from src.core.config import settings
from src.core.logger import get_logger, log_with_trace
from src.models.request import ParseTaskRequest
from typing import Dict
import regex as re
from datetime import datetime, timedelta
import pytz

logger = get_logger("parse_service")


class ParseService:
    def __init__(self):
        self.llm_service = BlueLMService()
        self.timezone = pytz.timezone(settings.DEFAULT_TIMEZONE)

    def fallback_parse(self, source_text: str, trace_id: str) -> Dict:
        log_with_trace(logger, "WARNING", "启用正则降级解析", trace_id)

        time_patterns = [
            r"(\d+)月(\d+)日(\d+)点",
            r"明天(\d+)点",
            r"(\d+)点(\d+)分",
            r"下午(\d+)点"
        ]

        now = datetime.now(self.timezone)
        start_time = now + timedelta(days=1)
        start_time = start_time.replace(hour=15, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)

        for pattern in time_patterns:
            match = re.search(pattern, source_text)
            if match:
                pass

        return {
            "title": source_text,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": None,
            "participants": [],
            "confidence": 0.5,
            "ambiguities": ["time"],
            "timezone": settings.DEFAULT_TIMEZONE
        }

    async def parse(self, request: ParseTaskRequest, trace_id: str) -> Dict:
        if not request.source_text.strip():
            raise ValueError("解析文本为空（错误码1001）")

        llm_result = await self.llm_service.parse_task(
            source_text=request.source_text,
            context=request.context,
            trace_id=trace_id
        )

        if not llm_result or llm_result.get("confidence", 0) < 0.6:
            llm_result = self.fallback_parse(request.source_text, trace_id)

        if llm_result.get("end_time") is None:
            if llm_result.get("start_time"):
                start_dt = datetime.fromisoformat(llm_result["start_time"])
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=self.timezone)
                llm_result["end_time"] = (start_dt + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)).isoformat()
            else:
                now = datetime.now(self.timezone)
                llm_result["start_time"] = (now + timedelta(hours=1)).isoformat()
                llm_result["end_time"] = (now + timedelta(hours=1) + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)).isoformat()

        if not llm_result.get("location"):
            llm_result["location"] = "未知"
        if not llm_result.get("start_time"):
            llm_result["start_time"] = datetime.now(self.timezone).isoformat()
            llm_result["needs_confirmation"] = True

        llm_result.setdefault("timezone",
                              request.context.get("user_preferences", {}).get("timezone", settings.DEFAULT_TIMEZONE))
        llm_result.setdefault("participants", [])
        llm_result.setdefault("location", "未知")

        return llm_result
