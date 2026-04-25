from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from src.core.logger import get_logger, log_with_trace
from typing import Dict, List

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger("websocket")

# 存储活动连接
active_connections: Dict[str, List[WebSocket]] = {}


@router.websocket("/tasks")
async def websocket_endpoint(websocket: WebSocket, trace_id: str = None):
    """任务实时推送WebSocket"""
    # 生成trace_id（如果未传）
    if not trace_id:
        trace_id = websocket.headers.get("X-Trace-ID", "unknown")

    # 接受连接
    await websocket.accept()
    # 存储连接
    if trace_id not in active_connections:
        active_connections[trace_id] = []
    active_connections[trace_id].append(websocket)

    log_with_trace(logger, "INFO", "WebSocket连接建立", trace_id)

    try:
        # 保持连接
        while True:
            # 接收客户端消息（可选）
            data = await websocket.receive_text()
            log_with_trace(logger, "INFO", f"收到客户端消息：{data}", trace_id)

    except WebSocketDisconnect:
        # 移除连接
        active_connections[trace_id].remove(websocket)
        if not active_connections[trace_id]:
            del active_connections[trace_id]
        log_with_trace(logger, "INFO", "WebSocket连接断开", trace_id)


# 推送消息函数（供其他服务调用）
async def push_task_update(trace_id: str, message: Dict):
    """推送任务状态更新"""
    if trace_id not in active_connections:
        return

    for connection in active_connections[trace_id]:
        try:
            await connection.send_json(message)
        except Exception as e:
            log_with_trace(logger, "ERROR", f"推送消息失败：{str(e)}", trace_id)