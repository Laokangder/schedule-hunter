from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone, timedelta
from src.services.task_service import TaskService
from src.core.logger import get_logger
import traceback

logger = get_logger("reminder_service")

scheduler = None


async def check_reminders():
    try:
        current_time = datetime.now().astimezone()
        print(f"[Timer Heartbeat] Checking tasks at {current_time.strftime('%H:%M:%S')}...")

        task_service = TaskService()
        pending_tasks = task_service.get_pending_reminders()

        for task in pending_tasks:
            logger.info(f"触发提醒：{task['task_id']} - {task['title']}")
            offset_minutes = task["due_offset_minutes"]
            task_service.mark_reminded(task['task_id'], offset_minutes)

            from src.api.v1.websocket import broadcast_reminder
            await broadcast_reminder(task['task_id'], task['title'], offset_minutes)

    except Exception as e:
        logger.error(f"提醒调度异常：{str(e)}\n{traceback.format_exc()}")


async def expire_overdue_tasks():
    try:
        current_time = datetime.now().astimezone()
        print(f"[Timer Heartbeat] Expire check at {current_time.strftime('%H:%M:%S')}...")

        task_service = TaskService()
        count = task_service.expire_overdue_tasks()
        if count > 0:
            logger.info(f"过期任务处理完成：{count}个")

            from src.api.v1.websocket import broadcast_task_update
            await broadcast_task_update("bulk_expire", "expired")

    except Exception as e:
        logger.error(f"过期判定异常：{str(e)}\n{traceback.format_exc()}")


def start_reminder_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        return
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_reminders,
        trigger=IntervalTrigger(seconds=30),
        id="reminder_check",
        name="检查待提醒任务",
        replace_existing=True
    )
    scheduler.add_job(
        expire_overdue_tasks,
        trigger=IntervalTrigger(seconds=30),
        id="expire_check",
        name="检查过期任务",
        replace_existing=True
    )
    scheduler.start()
    logger.info("调度器已启动")


def stop_reminder_scheduler():
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("调度器已停止")
    scheduler = None
