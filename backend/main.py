import logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.v1.task import router as task_router
from src.api.v1.websocket import router as websocket_router
from src.core.logger import TraceIDMiddleware, get_logger
from src.core.config import settings
from src.services.reminder_service import start_reminder_scheduler, stop_reminder_scheduler
import uvicorn

logger = get_logger("main")

app = FastAPI(
    title="Schedule Hunter API",
    version="1.0.0",
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TraceIDMiddleware)

app.include_router(task_router)
app.include_router(websocket_router)


@app.on_event("startup")
async def startup_event():
    start_reminder_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    stop_reminder_scheduler()


@app.get("/")
async def root():
    return {
        "message": "Schedule Hunter Backend API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info"
    )