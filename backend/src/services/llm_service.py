import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
import httpx


class BlueLMService:
    def __init__(self):
        raw_base = "https://api.deepseek.com/v1"
        if not raw_base.startswith(("http://", "https://")):
            raw_base = "https://" + raw_base
        self.api_base = raw_base
        self.model = "deepseek-v4-flash"
        self.api_key = "sk-09d9dadd8eab4bb18c59b11e772fcf83"
        self.timeout = 30.0
        self.default_duration_minutes = 60

    def _build_prompt(self, source_text: str) -> list:
        now = datetime.now(timezone(timedelta(hours=8)))
        system_prompt = (
            "你是一个极度精准的日程意图提取助手。"
            f"当前系统时间：{now.isoformat()}。"
            "从用户的口语化文本中，提取出title（任务标题——必须去除地点、人物、冗余修饰词，只保留核心动名词，如\"吃饭\"\"谈合作\"\"开会\"）、"
            "start_time（开始时间，必须为ISO 8601格式，"
            "结合当前系统时间进行相对时间计算推演）、end_time（结束时间，ISO 8601格式）、"
            "location（地点——遇到\"在...\"\"去...\"\"到...\"等字眼必须提取为location，没有则设为null）、"
            "confidence（置信度0.0-1.0）。"
            "示例1：输入\"明天下午3点去望京SOHO找张总谈合作\" 输出{\"title\":\"谈合作\",\"start_time\":\"2026-04-26T15:00:00+08:00\",\"end_time\":\"2026-04-26T16:00:00+08:00\",\"location\":\"望京SOHO\",\"confidence\":0.95}"
            "示例2：输入\"在和平饭店吃饭\" 输出{\"title\":\"吃饭\",\"start_time\":\"2026-04-25T12:00:00+08:00\",\"end_time\":\"2026-04-25T13:00:00+08:00\",\"location\":\"和平饭店\",\"confidence\":0.95}"
            "绝对不要输出任何markdown标记、思考过程或解释性文字。"
            "仅输出JSON字符串，格式："
            '{"title":"...","start_time":"...","end_time":"...","location":null或"...","confidence":0.0-1.0}'
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": source_text}
        ]

    async def parse_task(self, source_text: str, trace_id: str, context: Dict = {}) -> Optional[Dict]:
        messages = self._build_prompt(source_text)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 512
        }

        endpoint = self.api_base.rstrip("/") + "/chat/completions"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            response.raise_for_status()
            response_data = response.json()

        raw_content = response_data["choices"][0]["message"]["content"]

        print("\n" + "="*50 + "\n🔥 [DEBUG] 大模型原始返回内容开始:\n" + raw_content + "\n" + "="*50 + "\n")

        raw_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
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
            "participants": [],
            "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.5)))),
            "ambiguities": []
        }

        if not result["start_time"] or not result["end_time"]:
            now = datetime.now(timezone(timedelta(hours=8)))
            result["start_time"] = (now + timedelta(hours=1)).isoformat()
            result["end_time"] = (now + timedelta(hours=1) + timedelta(minutes=self.default_duration_minutes)).isoformat()
            result["confidence"] = 0.3

        return result

    def _fallback_parse(self, source_text: str) -> Dict:
        now = datetime.now(timezone(timedelta(hours=8)))
        start_time = now + timedelta(hours=1)
        start_time = start_time.replace(second=0, microsecond=0)
        end_time = start_time + timedelta(minutes=self.default_duration_minutes)
        return {
            "title": source_text[:30] if source_text else "未识别任务",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "location": None,
            "participants": [],
            "confidence": 0.1,
            "ambiguities": []
        }
