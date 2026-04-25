from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class BaseResponse(BaseModel):
    code: int
    message: str
    trace_id: str
    data: Any = None


class ConflictItem(BaseModel):
    task_id: str
    conflict_type: str
    conflict_level: str
    detail: Optional[str] = None
    suggestions: List[str] = []


class Suggestion(BaseModel):
    action: str
    suggested_time: Optional[str] = None
    suggested_duration_minutes: Optional[int] = None
    description: str


class Ambiguity(BaseModel):
    field: str
    question: str
    options: List[str] = []


class ParseTaskResponseData(BaseModel):
    parsed: Dict[str, Any]
    is_conflict: bool = False
    conflict: Optional[ConflictItem] = None
    suggestions: List[Suggestion] = []
    needs_confirmation: bool = False
    ambiguities: List[Ambiguity] = []


class CreateTaskResponseData(BaseModel):
    task_id: str
    status: str


class ConflictCheckResponseData(BaseModel):
    has_conflict: bool
    conflict_tasks: list = []


class WebSocketPushData(BaseModel):
    type: str
    payload: Dict[str, Any]


class TaskListResponseData(BaseModel):
    task_list: List[Dict[str, Any]]
