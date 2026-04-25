from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal
from datetime import datetime

# 解析任务请求体
class UserPreferences(BaseModel):
    default_duration_minutes: Optional[int] = 60
    timezone: Optional[str] = "Asia/Shanghai"

class MetaData(BaseModel):
    input_type: Literal["notification", "clipboard", "intent", "manual"]
    client_timestamp: str  # ISO 8601格式
    app_version: Optional[str] = None
    language: Optional[str] = "zh-CN"

class ParseTaskRequest(BaseModel):
    request_id: str
    source_text: str = Field(max_length=500)
    context: Optional[Dict] = Field(default={"recent_tasks": [], "user_preferences": {}})
    meta: MetaData

# 创建任务请求体
class ParsedTask(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = []
    timezone: Optional[str] = "Asia/Shanghai"

class ReminderPolicy(BaseModel):
    enabled: bool = True
    offset_minutes: List[int] = [30, 10, 5]

class CreateTaskRequest(BaseModel):
    request_id: str
    source_text: str
    parsed: ParsedTask
    priority: Literal["low", "normal", "high"] = "normal"
    reminder_policy: Optional[ReminderPolicy] = ReminderPolicy()
    meta: MetaData

# 冲突检测请求体
class CandidateTask(BaseModel):
    title: str
    start_time: str
    end_time: Optional[str] = None
    location: Optional[str] = None

class ConflictCheckScope(BaseModel):
    check_type: Literal["time_overlap", "travel_conflict", "priority_conflict"] = "time_overlap"
    include_travel_time: bool = True
    travel_buffer_minutes: Optional[int] = 20

class ConflictCheckRequest(BaseModel):
    request_id: str
    candidate: CandidateTask
    scope: ConflictCheckScope
