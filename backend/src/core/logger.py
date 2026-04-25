import logging
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from src.core.config import settings

# 日志配置
log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - trace_id=%(trace_id)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


# Trace ID 中间件
class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 生成/获取trace_id
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()).replace("-", ""))
        request.state.trace_id = trace_id

        # 注入trace_id到日志上下文
        logger = get_logger("trace")
        logger.info(f"Request start: {request.method} {request.url}", extra={"trace_id": trace_id})

        # 处理请求
        response: Response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        # 日志记录
        logger.info(f"Request end: {response.status_code}", extra={"trace_id": trace_id})
        return response


# 日志工具函数（自动携带trace_id）
def log_with_trace(logger: logging.Logger, level: str, message: str, trace_id: str):
    extra = {"trace_id": trace_id}
    if level == "INFO":
        logger.info(message, extra=extra)
    elif level == "ERROR":
        logger.error(message, extra=extra)
    elif level == "WARNING":
        logger.warning(message, extra=extra)