import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from fastapi import FastAPI
from src.api.v1.task import router as task_router
from src.api.v1.websocket import router as websocket_router
from src.core.logger import TraceIDMiddleware, get_logger
from src.core.config import settings
import uvicorn

# 初始化FastAPI
app = FastAPI(
    title="Schedule Hunter API",
    version="1.0.0",
    debug=settings.DEBUG
)

# 添加中间件
app.add_middleware(TraceIDMiddleware)

# 注册路由
app.include_router(task_router)
app.include_router(websocket_router)

# 根路由
@app.get("/")
async def root():
    return {
        "message": "Schedule Hunter Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 启动服务
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
