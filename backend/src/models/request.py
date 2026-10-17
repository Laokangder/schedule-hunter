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
    participants: Optional[List[str]] = Field(default_factory=list)
    timezone: Optional[str] = "Asia/Shanghai"

class ReminderPolicy(BaseModel):
    enabled: bool = True
    offset_minutes: List[int] = Field(default_factory=lambda: [30, 10, 5])

class CreateTaskRequest(BaseModel):
    request_id: str
    source_text: str
    parsed: ParsedTask
    priority: Literal["low", "normal", "high"] = "normal"
    reminder_policy: Optional[ReminderPolicy] = Field(default_factory=ReminderPolicy)
    meta: MetaData


class UpdateTaskRequest(BaseModel):
    request_id: str
    title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    location: Optional[str] = None
    participants: Optional[List[str]] = None
    priority: Optional[Literal["low", "normal", "high"]] = None
    reminder_policy: Optional[ReminderPolicy] = None


class CandidateCreateRequest(BaseModel):
    request_id: str
    source_type: Literal["notification", "intent", "manual", "clipboard"] = "manual"
    source_package: Optional[str] = None
    source_app_name: Optional[str] = None
    source_text: str = Field(max_length=500)
    parsed: Dict = Field(default_factory=dict)
    intent_type: Optional[Literal["create", "update", "cancel"]] = None
    target_task_id: Optional[str] = None
    changes: Dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    match_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class CandidateUpdateRequest(BaseModel):
    request_id: str
    parsed: Optional[Dict] = None
    changes: Optional[Dict] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[Literal["pending", "ignored"]] = None
    target_task_id: Optional[str] = None


class CandidateConfirmRequest(BaseModel):
    request_id: str


class CandidateSnoozeRequest(BaseModel):
    request_id: str
    duration_minutes: Optional[Literal[10, 60]] = None
    snoozed_until: Optional[str] = None


class WorkingHours(BaseModel):
    start: str = "09:00"
    end: str = "18:00"


class FreeSlotsRequest(BaseModel):
    duration_minutes: int = Field(gt=0, le=1440)
    range_start: str
    range_end: str
    working_hours: WorkingHours = Field(default_factory=WorkingHours)
    buffer_minutes: int = Field(default=0, ge=0, le=720)
    preferred_start: Optional[str] = None

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
