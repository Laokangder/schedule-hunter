import logging
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from src.core.config import settings

log_dir = Path("./logs")
log_dir.mkdir(exist_ok=True)


class SafeFormatter(logging.Formatter):
    def format(self, record):
        if not hasattr(record, 'trace_id'):
            record.trace_id = 'N/A'
        return super().format(record)


file_handler = logging.FileHandler(settings.LOG_FILE)
file_handler.setFormatter(SafeFormatter("%(asctime)s - %(name)s - %(levelname)s - trace_id=%(trace_id)s - %(message)s"))

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(SafeFormatter("%(asctime)s - %(name)s - %(levelname)s - trace_id=%(trace_id)s - %(message)s"))

logging.basicConfig(
    level=logging.getLevelName(settings.LOG_LEVEL),
    handlers=[file_handler, stream_handler]
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()).replace("-", ""))
        request.state.trace_id = trace_id

        logger = get_logger("trace")
        logger.info(f"Request start: {request.method} {request.url}", extra={"trace_id": trace_id})

        response: Response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id

        logger.info(f"Request end: {response.status_code}", extra={"trace_id": trace_id})
        return response


def log_with_trace(logger: logging.Logger, level: str, message: str, trace_id: str):
    extra = {"trace_id": trace_id}
    if level == "INFO":
        logger.info(message, extra=extra)
    elif level == "ERROR":
        logger.error(message, extra=extra)
    elif level == "WARNING":
        logger.warning(message, extra=extra)
    elif level == "DEBUG":
        logger.debug(message, extra=extra)
