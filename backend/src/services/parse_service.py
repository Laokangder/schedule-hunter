from src.services.llm_service import LLMService
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
        self.llm_service = LLMService()
        self.timezone = pytz.timezone(settings.DEFAULT_TIMEZONE)

    @staticmethod
    def _parse_chinese_number(value: str) -> int:
        if value.isdigit():
            return int(value)
        digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
                  "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if "十" in value:
            tens, ones = value.split("十", 1)
            return (digits.get(tens, 1) * 10) + digits.get(ones, 0)
        return digits.get(value, 0)

    def _parse_relative_start(self, source_text: str, now: datetime):
        match = re.search(r"([0-9零〇一二两三四五六七八九十]+)\s*(分钟|小时)后", source_text)
        if not match:
            return None
        amount = self._parse_chinese_number(match.group(1))
        if amount <= 0:
            return None
        delta = timedelta(minutes=amount) if match.group(2) == "分钟" else timedelta(hours=amount)
        return now + delta

    @staticmethod
    def _extract_title_and_location(source_text: str):
        actions = "吃饭|睡觉|开会|聚餐|见面|看电影|跑步|运动|学习|上课|复习|工作|买东西|取快递|打电话"
        location = None
        location_match = re.search(rf"(?:在|去)(?P<location>[^，,。.!！？]+?)(?P<action>{actions})", source_text)
        if location_match and location_match.group("location").strip():
            location = location_match.group("location").strip()

        title = source_text
        title = re.sub(r"[0-9零〇一二两三四五六七八九十]+\s*(?:分钟|小时)后", "", title)
        title = re.sub(r"(?:今天|明天|后天|大后天)", "", title)
        title = re.sub(r"\d{1,2}月\d{1,2}[日号]?", "", title)
        title = re.sub(r"(?:上午|中午|下午|晚上|凌晨)?\s*(?:[0-9]{1,2}|十一|十二|十|[一二两三四五六七八九])(?:点|时|:)(?:半|[0-9]{1,2}分?)?", "", title)
        if location_match:
            title = location_match.group("action")
        else:
            title = re.sub(r"^(?:去|要|准备|计划|打算)", "", title.strip())
        title = title.strip(" ，,。.!！？") or source_text
        return title, location

    def _apply_text_rules(self, source_text: str, result: Dict, trace_id: str) -> Dict:
        before = dict(result)
        now = datetime.now(self.timezone)
        relative_start = self._parse_relative_start(source_text, now)
        extracted_title, extracted_location = self._extract_title_and_location(source_text)

        if relative_start:
            result["start_time"] = relative_start.isoformat()
            result["end_time"] = (relative_start + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)).isoformat()
            result["ambiguities"] = [item for item in result.get("ambiguities", []) if item != "time"]
            result["needs_confirmation"] = False
            result["confidence"] = max(float(result.get("confidence", 0)), 0.9)

        if extracted_location and result.get("location") in (None, "", "未知"):
            result["location"] = extracted_location

        if (relative_start or result.get("ai_fallback") or result.get("title") in (None, "", source_text)) and extracted_title:
            result["title"] = extracted_title

        if result != before:
            log_with_trace(
                logger,
                "INFO",
                "RULE_APPLIED",
                trace_id,
            )
        return result

    def fallback_parse(self, source_text: str, trace_id: str) -> Dict:
        log_with_trace(logger, "WARNING", "启用正则降级解析", trace_id)

        now = datetime.now(self.timezone)
        default_start = now + timedelta(hours=1)
        if default_start.hour >= 23:
            default_start = default_start.replace(hour=22, minute=59, second=59)
        default_end = default_start + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)

        relative_start = self._parse_relative_start(source_text, now)
        parsed_time = False
        if relative_start:
            default_start = relative_start
            default_end = default_start + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)
            parsed_time = True

        day_offset = 2 if "后天" in source_text else 1 if "明天" in source_text else 0
        target_date = (now + timedelta(days=day_offset)).date()
        month_day = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", source_text)
        if month_day:
            year = now.year
            target_date = now.replace(year=year, month=int(month_day.group(1)), day=int(month_day.group(2))).date()
            if target_date < now.date():
                target_date = target_date.replace(year=year + 1)

        chinese_numbers = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
                           "十一": 11, "十二": 12}
        time_match = re.search(r"(上午|中午|下午|晚上|凌晨)?\s*([0-9]{1,2}|十一|十二|十|[一二两三四五六七八九])(?:点|时|:)(半|[0-9]{1,2}分?)?", source_text)
        if time_match and not relative_start:
            period, hour_text, minute_text = time_match.groups()
            hour = int(hour_text) if hour_text.isdigit() else chinese_numbers[hour_text]
            minute = 30 if minute_text == "半" else int((minute_text or "0").rstrip("分"))
            if period in ("下午", "晚上") and hour < 12:
                hour += 12
            elif period == "中午" and hour < 11:
                hour += 12
            elif period == "凌晨" and hour == 12:
                hour = 0
            default_start = self.timezone.localize(datetime.combine(target_date, datetime.min.time()).replace(hour=hour, minute=minute))
            default_end = default_start + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)
            parsed_time = True

        title, location = self._extract_title_and_location(source_text)
        return {
            "title": title,
            "start_time": default_start.isoformat(),
            "end_time": default_end.isoformat(),
            "location": location,
            "participants": [],
            "confidence": 0.75 if parsed_time else 0.5,
            "ambiguities": [] if parsed_time else ["time"],
            "timezone": settings.DEFAULT_TIMEZONE,
            "ai_fallback": True,
            "needs_confirmation": not parsed_time,
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
            log_with_trace(
                logger,
                "WARNING",
                "REGEX_FALLBACK",
                trace_id,
            )
            llm_result = self.fallback_parse(request.source_text, trace_id)
        else:
            log_with_trace(
                logger,
                "INFO",
                f"LLM_ACCEPTED confidence={llm_result.get('confidence', 0)}",
                trace_id,
            )

        llm_result = self._apply_text_rules(request.source_text, llm_result, trace_id)

        now = datetime.now(self.timezone)
        default_start = now + timedelta(hours=1)
        if default_start.hour >= 23:
            default_start = default_start.replace(hour=22, minute=59, second=59)
        default_end = default_start + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)

        if llm_result.get("end_time") is None:
            if llm_result.get("start_time"):
                start_dt = datetime.fromisoformat(llm_result["start_time"])
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=self.timezone)
                llm_result["end_time"] = (start_dt + timedelta(minutes=settings.DEFAULT_DURATION_MINUTES)).isoformat()
            else:
                llm_result["start_time"] = default_start.isoformat()
                llm_result["end_time"] = default_end.isoformat()
                llm_result["needs_confirmation"] = True

        if not llm_result.get("location"):
            llm_result["location"] = "未知"
        if not llm_result.get("start_time"):
            llm_result["start_time"] = default_start.isoformat()
            llm_result["needs_confirmation"] = True

        llm_result.setdefault("timezone",
                              request.context.get("user_preferences", {}).get("timezone", settings.DEFAULT_TIMEZONE))
        llm_result.setdefault("participants", [])
        llm_result.setdefault("location", "未知")

        log_with_trace(
            logger,
            "INFO",
            f"RULE_NORMALIZED confidence={llm_result.get('confidence', 0)}",
            trace_id,
        )

        return llm_result
