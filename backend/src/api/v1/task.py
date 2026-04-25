from fastapi import APIRouter, Request, HTTPException
from typing import Optional
from src.models.request import ParseTaskRequest, CreateTaskRequest, ConflictCheckRequest
from src.models.response import BaseResponse, ParseTaskResponseData, CreateTaskResponseData, ConflictCheckResponseData, \
    TaskListResponseData, ConflictItem, Suggestion, Ambiguity
from src.services.parse_service import ParseService
from src.services.task_service import TaskService
from src.services.conflict_service import ConflictService
from src.core.logger import get_logger, log_with_trace

router = APIRouter(tags=["task"])
logger = get_logger("task_api")

parse_service = ParseService()
task_service = TaskService()
conflict_service = ConflictService()


@router.post("/api/v1/task/parse")
async def parse_task(request: Request, body: ParseTaskRequest):
    trace_id = request.state.trace_id
    try:
        parsed_data = await parse_service.parse(body, trace_id)
        if not parsed_data:
            raise HTTPException(status_code=400, detail="解析失败（错误码1002）")

        conflict_check = conflict_service.check_conflict(
            candidate=parsed_data,
            scope={"check_type": "time_overlap", "include_travel_time": True, "travel_buffer_minutes": 20},
            trace_id=trace_id
        )

        suggestions = conflict_service.generate_suggestions(parsed_data,
                                                            conflict_check.get("conflict_type", "time_overlap"))

        conflict_obj = None
        if conflict_check["has_conflict"] and conflict_check["conflicts"]:
            c = conflict_check["conflicts"][0]
            conflict_obj = ConflictItem(
                task_id=c.get("task_id", ""),
                conflict_type=c.get("conflict_type", "time_overlap"),
                conflict_level=c.get("conflict_level", "medium"),
                detail=c.get("detail", ""),
                suggestions=c.get("suggestions", [])
            )

        suggestion_objs = [Suggestion(**s) for s in suggestions]

        raw_ambiguities = parsed_data.get("ambiguities", [])
        processed_ambiguities = []
        for item in raw_ambiguities:
            if isinstance(item, dict):
                processed_ambiguities.append(Ambiguity(**item))
            elif isinstance(item, str):
                processed_ambiguities.append(Ambiguity(field=item, question=f"请确认{item}", options=[]))
            else:
                processed_ambiguities.append(Ambiguity(field=str(item), question=f"请确认{item}", options=[]))

        response_data = ParseTaskResponseData(
            parsed=parsed_data,
            is_conflict=conflict_check["has_conflict"],
            conflict=conflict_obj,
            suggestions=suggestion_objs,
            needs_confirmation=parsed_data.get("confidence", 0) < 0.6,
            ambiguities=processed_ambiguities
        )

        return BaseResponse(
            code=0,
            message="parsed",
            data=response_data.model_dump(),
            trace_id=trace_id
        )

    except ValueError as e:
        if "1001" in str(e):
            return BaseResponse(code=1001, message="解析文本为空", data={}, trace_id=trace_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_with_trace(logger, "ERROR", f"解析接口异常：{repr(e)}", trace_id)
        return BaseResponse(code=5000, message="服务器内部错误", data={}, trace_id=trace_id)


@router.post("/api/v1/tasks")
async def create_task(request: Request, body: CreateTaskRequest):
    trace_id = request.state.trace_id
    try:
        task_data = task_service.create_task(body, trace_id)
        response_data = CreateTaskResponseData(**task_data)

        return BaseResponse(
            code=0,
            message="created",
            data=response_data.model_dump(),
            trace_id=trace_id
        )

    except ValueError as e:
        if "3001" in str(e):
            return BaseResponse(code=3001, message="任务写入失败", data={}, trace_id=trace_id)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        log_with_trace(logger, "ERROR", f"创建任务异常：{repr(e)}", trace_id)
        return BaseResponse(code=5000, message="服务器内部错误", data={}, trace_id=trace_id)


@router.get("/api/v1/tasks")
async def get_tasks(request: Request, date: Optional[str] = None, status: Optional[str] = None):
    trace_id = request.state.trace_id
    try:
        task_data = task_service.get_tasks_by_date(date, status, trace_id)
        response_data = TaskListResponseData(**task_data)

        return BaseResponse(
            code=0,
            message="ok",
            data=response_data.model_dump(),
            trace_id=trace_id
        )

    except Exception as e:
        log_with_trace(logger, "ERROR", f"查询任务异常：{repr(e)}", trace_id)
        return BaseResponse(code=5000, message="服务器内部错误", data={}, trace_id=trace_id)


@router.post("/api/v1/tasks/conflict-check")
async def conflict_check(request: Request, body: ConflictCheckRequest):
    trace_id = request.state.trace_id
    try:
        conflict_data = conflict_service.check_conflict(
            candidate=body.candidate,
            scope=body.scope,
            trace_id=trace_id
        )

        response_data = ConflictCheckResponseData(**conflict_data)
        return BaseResponse(
            code=0,
            message="checked",
            data=response_data.model_dump(),
            trace_id=trace_id
        )

    except Exception as e:
        log_with_trace(logger, "ERROR", f"冲突检测异常：{repr(e)}", trace_id)
        return BaseResponse(code=2002, message="冲突检测失败", data={}, trace_id=trace_id)
