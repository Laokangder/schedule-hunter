from typing import Optional

from fastapi import APIRouter, Request

from src.core.logger import get_logger, log_with_trace
from src.models.request import (
    CandidateConfirmRequest,
    CandidateCreateRequest,
    CandidateSnoozeRequest,
    CandidateUpdateRequest,
)
from src.models.response import BaseResponse
from src.services.candidate_service import CandidateService


router = APIRouter(prefix="/api/v1/candidates", tags=["candidate"])
logger = get_logger("candidate_api")
candidate_service = CandidateService()


def _error_response(exc: Exception, trace_id: str) -> BaseResponse:
    message = str(exc)
    if "2001" in message:
        return BaseResponse(code=2001, message="时间非法", data={}, trace_id=trace_id)
    if "4001" in message:
        return BaseResponse(code=4001, message="任务不存在", data={}, trace_id=trace_id)
    return BaseResponse(code=4002, message=message, data={}, trace_id=trace_id)


@router.post("")
async def create_candidate(request: Request, body: CandidateCreateRequest):
    trace_id = request.state.trace_id
    try:
        result = candidate_service.create_or_merge(body)
        return BaseResponse(code=0, message="candidate ready", data=result, trace_id=trace_id)
    except Exception as exc:
        log_with_trace(logger, "ERROR", f"候选创建失败：{type(exc).__name__}", trace_id)
        return BaseResponse(code=5000, message="候选创建失败", data={}, trace_id=trace_id)


@router.get("")
async def list_candidates(
    request: Request,
    status: Optional[str] = None,
    due: bool = False,
    now: Optional[str] = None,
):
    trace_id = request.state.trace_id
    try:
        candidates = candidate_service.list(status=status, due=due, now=now)
        return BaseResponse(code=0, message="ok", data={"candidates": candidates}, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(exc, trace_id)


@router.get("/{candidate_id}")
async def get_candidate(request: Request, candidate_id: str):
    trace_id = request.state.trace_id
    candidate = candidate_service.get(candidate_id)
    if not candidate:
        return BaseResponse(code=4001, message="候选不存在", data={}, trace_id=trace_id)
    return BaseResponse(code=0, message="ok", data=candidate, trace_id=trace_id)


@router.patch("/{candidate_id}")
async def update_candidate(request: Request, candidate_id: str, body: CandidateUpdateRequest):
    trace_id = request.state.trace_id
    try:
        candidate = candidate_service.update(candidate_id, body)
        if not candidate:
            return BaseResponse(code=4001, message="候选不存在", data={}, trace_id=trace_id)
        return BaseResponse(code=0, message="updated", data=candidate, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(exc, trace_id)


@router.post("/{candidate_id}/confirm")
async def confirm_candidate(request: Request, candidate_id: str, body: CandidateConfirmRequest):
    trace_id = request.state.trace_id
    try:
        result = candidate_service.confirm(candidate_id, body.request_id)
        if not result:
            return BaseResponse(code=4001, message="候选不存在", data={}, trace_id=trace_id)
        task = result.get("task") or {}
        if task.get("task_id") and not result.get("idempotent"):
            from src.api.v1.websocket import broadcast_task_update
            await broadcast_task_update(task["task_id"], task.get("status", "updated"))
        return BaseResponse(code=0, message="confirmed", data=result, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(exc, trace_id)


@router.post("/{candidate_id}/snooze")
async def snooze_candidate(request: Request, candidate_id: str, body: CandidateSnoozeRequest):
    trace_id = request.state.trace_id
    try:
        candidate = candidate_service.snooze(candidate_id, body)
        if not candidate:
            return BaseResponse(code=4001, message="候选不存在", data={}, trace_id=trace_id)
        return BaseResponse(code=0, message="snoozed", data=candidate, trace_id=trace_id)
    except ValueError as exc:
        return _error_response(exc, trace_id)
