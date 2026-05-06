import httpx
import json
import re
import os
from datetime import datetime, timezone, timedelta
from typing import Dict
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("llm_service")


class LLMService:
    def __init__(self):
        self.api_key = settings.LLM_API_KEY or os.getenv("LLM_API_KEY") or settings.BLUELM_API_KEY
        self.api_url = settings.LLM_API_URL or os.getenv("LLM_API_URL") or settings.BLUELM_API_URL
        self.model = settings.LLM_MODEL
        self.default_duration_minutes = 60
        self.timeout = 15.0

    async def parse_task(self, source_text: str, context: Dict = None, trace_id: str = "") -> Dict:
        try:
            return await self._call_llm_api(source_text)
        except TimeoutError:
            logger.warning(f"LLM API timeout: {source_text[:50]}")
            result = self._fallback_parse(source_text)
            result["ai_fallback"] = True
            return result
        except Exception as e:
            logger.error(f"LLM API error: {str(e)}")
            result = self._fallback_parse(source_text)
            result["ai_fallback"] = True
            return result

    async def _call_llm_api(self, source_text: str) -> Dict:
        current_date = datetime.now().strftime('%Y-%m-%d')

        system_prompt = f"""你是一个精确的时间提取助手。

【系统基准日期】{current_date}

【核心规则】
1. 日期锚定：若用户未提及具体日期词汇（"明天"、"后天"、"28号"等），一律使用基准日期 {current_date}
2. 时间绝对忠诚：用户输入的时间必须原样提取并转为24小时制，绝不擅自修改
3. 禁止猜测：若用户未提供时间，设置 needs_confirmation=true，不擅自填充

【必须严格遵循的JSON格式】
{{
  "title": "事件名称",
  "start_time": "YYYY-MM-DDTHH:MM:SS+08:00",
  "end_time": "YYYY-MM-DDTHH:MM:SS+08:00",
  "confidence": 0.95,
  "needs_confirmation": false,
  "ambiguities": []
}}

【必须严格遵循的示例】

示例1：
输入：明天上午八点半开会
必须输出：{{"title":"开会","start_time":"2026-04-29T08:30:00+08:00","end_time":"2026-04-29T09:30:00+08:00","confidence":0.95,"needs_confirmation":false,"ambiguities":[]}}

示例2：
输入：28日晚上七点吃饭
必须输出：{{"title":"吃饭","start_time":"2026-04-28T19:00:00+08:00","end_time":"2026-04-28T20:00:00+08:00","confidence":0.95,"needs_confirmation":false,"ambiguities":[]}}

示例3：
输入：下午三点去跑步
必须输出：{{"title":"去跑步","start_time":"{current_date}T15:00:00+08:00","end_time":"{current_date}T16:00:00+08:00","confidence":0.95,"needs_confirmation":false,"ambiguities":[]}}

示例4：
输入：洗澡
必须输出：{{"title":"洗澡","start_time":null,"end_time":null,"confidence":0.3,"needs_confirmation":true,"ambiguities":["time"]}}

请严格按上述JSON格式输出，不要添加任何其他文字。"""

        user_prompt = f"解析以下日程：{source_text}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        raw_content = re.sub(r'^```json\s*', '', raw_content, flags=re.DOTALL)
        raw_content = re.sub(r'^```\s*', '', raw_content, flags=re.DOTALL)
        raw_content = re.sub(r'\s*```$', '', raw_content, flags=re.DOTALL)
        raw_content = raw_content.strip()

        start_idx = raw_content.find('{')
        end_idx = raw_content.rfind('}')
        if start_idx != -1 and end_idx != -1:
            raw_content = raw_content[start_idx:end_idx+1]
        else:
            raise ValueError("no JSON block found in LLM response")

        parsed = json.loads(raw_content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM returned non-dict JSON")

        result = {
            "title": parsed.get("title", source_text[:30]),
            "start_time": parsed.get("start_time"),
            "end_time": parsed.get("end_time"),
            "location": parsed.get("location"),
            "participants": parsed.get("participants", []),
            "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
            "ambiguities": parsed.get("ambiguities", []),
            "ai_fallback": False,
            "needs_confirmation": not parsed.get("start_time") or not parsed.get("end_time")
        }

        return result

    def _fallback_parse(self, source_text: str) -> Dict:
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz)
        default_start = now + timedelta(hours=1)
        if default_start.hour >= 23:
            default_start = default_start.replace(hour=22, minute=59, second=59)
        default_end = default_start + timedelta(minutes=self.default_duration_minutes)
        return {
            "title": source_text[:30] if source_text else "未识别任务",
            "start_time": default_start.isoformat(),
            "end_time": default_end.isoformat(),
            "location": None,
            "participants": [],
            "confidence": 0.1,
            "ambiguities": ["time"],
            "ai_fallback": True,
            "needs_confirmation": True
        }
