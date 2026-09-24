import os
import tempfile
import unittest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock


TEST_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DB.close()
os.environ["DB_PATH"] = TEST_DB.name

from fastapi.testclient import TestClient
from main import app
from src.services.task_service import TaskService
from src.services.parse_service import ParseService
from src.models.request import MetaData, ParseTaskRequest


TZ = timezone(timedelta(hours=8))


def task_payload(title, start, end, request_id, reminders=None):
    return {
        "request_id": request_id,
        "source_text": title,
        "parsed": {
            "title": title,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "location": "测试地点",
            "participants": [],
            "timezone": "Asia/Shanghai",
        },
        "priority": "normal",
        "reminder_policy": reminders or {"enabled": True, "offset_minutes": [30, 10, 5]},
        "meta": {
            "input_type": "manual",
            "client_timestamp": datetime.now(TZ).isoformat(),
            "language": "zh-CN",
        },
    }


class ScheduleFlowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_context = TestClient(app)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_context.__exit__(None, None, None)
        try:
            os.unlink(TEST_DB.name)
        except PermissionError:
            pass

    def test_create_query_delete(self):
        now = datetime.now(TZ)
        payload = task_payload("新增删除测试", now + timedelta(hours=2), now + timedelta(hours=3), "req-crud")
        created = self.client.post("/api/v1/tasks", json=payload).json()
        self.assertEqual(created["code"], 0)
        self.assertIn("normalized", created["data"])
        task_id = created["data"]["task_id"]

        queried = self.client.get("/api/v1/tasks", params={"date": (now + timedelta(hours=2)).date().isoformat()}).json()
        self.assertTrue(any(task["task_id"] == task_id for task in queried["data"]["task_list"]))
        self.assertIn("island_state", queried["data"])

        deleted = self.client.delete(f"/api/v1/tasks/{task_id}").json()
        self.assertEqual(deleted["code"], 0)

    def test_overdue_moves_to_expired_and_bulk_delete(self):
        now = datetime.now(TZ)
        payload = task_payload("过期测试", now - timedelta(hours=2), now - timedelta(hours=1), "req-expired")
        task_id = self.client.post("/api/v1/tasks", json=payload).json()["data"]["task_id"]

        expired = self.client.get("/api/v1/tasks", params={"status": "expired"}).json()
        self.assertTrue(any(task["task_id"] == task_id for task in expired["data"]["task_list"]))

        cleared = self.client.delete("/api/v1/tasks/expired").json()
        self.assertEqual(cleared["code"], 0)
        self.assertGreaterEqual(cleared["data"]["deleted_count"], 1)

    def test_disabled_and_at_time_reminders(self):
        now = datetime.now(TZ)
        disabled = task_payload(
            "关闭提醒测试", now + timedelta(minutes=10), now + timedelta(minutes=20), "req-disabled",
            {"enabled": False, "offset_minutes": [30, 10, 5]},
        )
        self.client.post("/api/v1/tasks", json=disabled)
        due = task_payload(
            "到时提醒测试", now - timedelta(seconds=10), now + timedelta(minutes=10), "req-due",
            {"enabled": True, "offset_minutes": [5]},
        )
        due_id = self.client.post("/api/v1/tasks", json=due).json()["data"]["task_id"]

        service = TaskService()
        reminders = service.get_pending_reminders()
        self.assertFalse(any(task["title"] == "关闭提醒测试" for task in reminders))
        at_time = next(task for task in reminders if task["task_id"] == due_id)
        self.assertEqual(at_time["due_offset_minutes"], 0)
        self.assertTrue(service.mark_reminded(due_id, 0))
        self.assertFalse(any(task["task_id"] == due_id for task in service.get_pending_reminders()))

    def test_conflict_and_fallback_time_parse(self):
        now = datetime.now(TZ) + timedelta(days=3)
        existing = task_payload("冲突基准", now.replace(hour=14, minute=0), now.replace(hour=15, minute=0), "req-conflict-base")
        self.client.post("/api/v1/tasks", json=existing)
        checked = self.client.post("/api/v1/tasks/conflict-check", json={
            "request_id": "req-conflict-check",
            "candidate": {
                "title": "冲突候选",
                "start_time": now.replace(hour=14, minute=30).isoformat(),
                "end_time": now.replace(hour=15, minute=30).isoformat(),
                "location": "测试地点",
            },
            "scope": {"check_type": "time_overlap", "include_travel_time": True, "travel_buffer_minutes": 20},
        }).json()
        self.assertEqual(checked["code"], 0)
        self.assertTrue(checked["data"]["has_conflict"])
        self.assertTrue(checked["data"]["conflicts"])

        parsed = self.client.post("/api/v1/task/parse", json={
            "request_id": "req-parse",
            "source_text": "明天下午3点开项目会",
            "context": {"recent_tasks": [], "user_preferences": {"timezone": "Asia/Shanghai"}},
            "meta": {"input_type": "manual", "client_timestamp": datetime.now(TZ).isoformat()},
        }).json()
        self.assertEqual(parsed["code"], 0)
        start = datetime.fromisoformat(parsed["data"]["parsed"]["start_time"])
        self.assertEqual(start.hour, 15)
        self.assertEqual(start.date(), (datetime.now(TZ) + timedelta(days=1)).date())

    def test_relative_time_action_and_location_rules(self):
        service = ParseService()
        service.llm_service.parse_task = AsyncMock(return_value={
            "title": "去睡觉",
            "start_time": (datetime.now(TZ) + timedelta(minutes=10)).isoformat(),
            "end_time": (datetime.now(TZ) + timedelta(minutes=70)).isoformat(),
            "location": None,
            "participants": [],
            "confidence": 0.95,
            "ambiguities": [],
            "ai_fallback": False,
        })

        async def parse_text(text, request_id):
            return await service.parse(ParseTaskRequest(
                request_id=request_id,
                source_text=text,
                context={"recent_tasks": [], "user_preferences": {"timezone": "Asia/Shanghai"}},
                meta=MetaData(input_type="manual", client_timestamp=datetime.now(TZ).isoformat()),
            ), request_id)

        before = datetime.now(TZ)
        relative = asyncio.run(parse_text("十分钟后去睡觉", "req-relative"))
        relative_start = datetime.fromisoformat(relative["start_time"])
        self.assertEqual(relative["title"], "睡觉")
        self.assertAlmostEqual((relative_start - before).total_seconds(), 600, delta=3)

        service.llm_service.parse_task = AsyncMock(return_value={
            "title": "明天下午八点在味道元吃饭",
            "start_time": None,
            "end_time": None,
            "location": None,
            "participants": [],
            "confidence": 0.1,
            "ambiguities": ["time"],
            "ai_fallback": True,
        })
        meal = asyncio.run(parse_text("明天下午八点在味道元吃饭", "req-location"))
        meal_start = datetime.fromisoformat(meal["start_time"])
        self.assertEqual(meal["title"], "吃饭")
        self.assertEqual(meal["location"], "味道元")
        self.assertEqual(meal_start.hour, 20)
        self.assertEqual(meal_start.date(), (datetime.now(TZ) + timedelta(days=1)).date())


if __name__ == "__main__":
    unittest.main()
