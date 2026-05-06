from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.core.logger import get_logger
from typing import Dict, List
import json

router = APIRouter(prefix="/ws", tags=["websocket"])
logger = get_logger("websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        client_id = f"client_{id(websocket)}"
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"WebSocket连接建立: {client_id}")
        return client_id

    def disconnect(self, websocket: WebSocket, client_id: str):
        if client_id in self.active_connections:
            if websocket in self.active_connections[client_id]:
                self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"WebSocket连接断开: {client_id}")

    async def broadcast(self, message: dict):
        disconnected = []
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败 {client_id}: {str(e)}")
                    disconnected.append((connection, client_id))
        for conn, cid in disconnected:
            self.disconnect(conn, cid)

    async def send_personal(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {str(e)}")


ws_manager = ConnectionManager()


@router.websocket("/tasks")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"收到客户端消息: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, client_id)


async def broadcast_reminder(task_id: str, title: str):
    message = {
        "type": "REMINDER",
        "task_id": task_id,
        "title": title
    }
    await ws_manager.broadcast(message)
    logger.info(f"推送提醒: {task_id} - {title}")


async def broadcast_task_update(task_id: str, status: str):
    message = {
        "type": "TASK_UPDATED",
        "task_id": task_id,
        "status": status
    }
    await ws_manager.broadcast(message)
