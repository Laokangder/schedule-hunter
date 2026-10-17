import os
import sqlite3
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
from src.core.config import settings
from src.db.base import DBConnection


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


def candidate_payload(request_id, source_text, parsed, **overrides):
    payload = {
        "request_id": request_id,
        "source_type": "notification",
        "source_package": "com.example.source",
        "source_app_name": "测试来源",
        "source_text": source_text,
        "parsed": parsed,
        "confidence": 0.8,
    }
    payload.update(overrides)
    return payload


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

    def test_legacy_database_upgrade_preserves_tasks(self):
        legacy = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        legacy.close()
        conn = sqlite3.connect(legacy.name)
        conn.execute("""
            CREATE TABLE tasks (
                task_id TEXT PRIMARY KEY, request_id TEXT UNIQUE, title TEXT NOT NULL,
                start_time TEXT NOT NULL, end_time TEXT NOT NULL, location TEXT,
                participants TEXT, priority TEXT DEFAULT 'normal', reminder_policy TEXT,
                source_text TEXT, input_type TEXT, status TEXT DEFAULT 'scheduled',
                is_reminded INTEGER DEFAULT 0, reminded_offsets TEXT DEFAULT '[]', created_at TEXT
            )
        """)
        conn.execute("""
            INSERT INTO tasks (
                task_id, request_id, title, start_time, end_time, participants,
                reminder_policy, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "legacy-task", "legacy-request", "旧数据",
            "2026-10-18T09:00:00+08:00", "2026-10-18T10:00:00+08:00",
            "[]", "{}", "scheduled", "2026-10-17T00:00:00+08:00",
        ))
        conn.commit()
        conn.close()

        original_path = settings.DB_PATH
        try:
            settings.DB_PATH = legacy.name
            DBConnection()
            upgraded = sqlite3.connect(legacy.name)
            task = upgraded.execute("SELECT title FROM tasks WHERE task_id = ?", ("legacy-task",)).fetchone()
            columns = {row[1] for row in upgraded.execute("PRAGMA table_info(tasks)").fetchall()}
            candidate_table = upgraded.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'candidates'"
            ).fetchone()
            upgraded.close()
            self.assertEqual(task[0], "旧数据")
            self.assertIn("updated_at", columns)
            self.assertIsNotNone(candidate_table)
        finally:
            settings.DB_PATH = original_path
            os.unlink(legacy.name)

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

    def test_get_and_partial_update_task_resets_reminders(self):
        now = datetime.now(TZ) + timedelta(days=5)
        created = self.client.post(
            "/api/v1/tasks",
            json=task_payload("待改期会议", now, now + timedelta(hours=1), "req-update-base"),
        ).json()
        task_id = created["data"]["task_id"]
        service = TaskService()
        self.assertTrue(service.mark_reminded(task_id, 30))

        queried = self.client.get(f"/api/v1/tasks/{task_id}").json()
        self.assertEqual(queried["code"], 0)
        self.assertEqual(queried["data"]["title"], "待改期会议")

        new_start = now + timedelta(hours=2)
        updated = self.client.put(f"/api/v1/tasks/{task_id}", json={
            "request_id": "req-update-once",
            "title": "已改期会议",
            "start_time": new_start.isoformat(),
            "end_time": (new_start + timedelta(minutes=45)).isoformat(),
            "reminder_policy": {"enabled": True, "offset_minutes": [60, 10]},
        }).json()
        self.assertEqual(updated["code"], 0)
        self.assertEqual(updated["data"]["title"], "已改期会议")
        self.assertEqual(updated["data"]["reminded_offsets"], "[]")
        self.assertEqual(updated["data"]["is_reminded"], 0)

        repeated = self.client.put(f"/api/v1/tasks/{task_id}", json={
            "request_id": "req-update-once",
            "title": "不应覆盖幂等结果",
        }).json()
        self.assertEqual(repeated["data"]["title"], "已改期会议")
        self.assertTrue(repeated["data"]["idempotent"])

    def test_update_task_invalid_time_and_missing(self):
        now = datetime.now(TZ) + timedelta(days=6)
        task_id = self.client.post(
            "/api/v1/tasks",
            json=task_payload("非法改期", now, now + timedelta(hours=1), "req-invalid-update-base"),
        ).json()["data"]["task_id"]
        invalid = self.client.put(f"/api/v1/tasks/{task_id}", json={
            "request_id": "req-invalid-update",
            "end_time": (now - timedelta(minutes=1)).isoformat(),
        }).json()
        self.assertEqual(invalid["code"], 2001)
        missing = self.client.put("/api/v1/tasks/task_missing", json={
            "request_id": "req-missing-update",
            "title": "不存在",
        }).json()
        self.assertEqual(missing["code"], 4001)

    def test_candidate_crud_and_request_id_idempotency(self):
        start = datetime.now(TZ) + timedelta(days=7)
        parsed = {
            "title": "候选 CRUD",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "location": "A101",
            "participants": ["甲"],
        }
        payload = candidate_payload("cand-req-crud", "候选 CRUD 原文", parsed)
        first = self.client.post("/api/v1/candidates", json=payload).json()
        second = self.client.post("/api/v1/candidates", json=payload).json()
        self.assertEqual(first["code"], 0)
        self.assertEqual(first["data"]["candidate"]["candidate_id"], second["data"]["candidate"]["candidate_id"])
        self.assertTrue(second["data"]["idempotent"])
        self.assertEqual(second["data"]["candidate"]["seen_count"], 1)
        candidate_id = first["data"]["candidate"]["candidate_id"]

        detail = self.client.get(f"/api/v1/candidates/{candidate_id}").json()
        self.assertEqual(detail["data"]["parsed"]["title"], "候选 CRUD")
        listed = self.client.get("/api/v1/candidates", params={"status": "pending"}).json()
        self.assertTrue(any(item["candidate_id"] == candidate_id for item in listed["data"]["candidates"]))
        patched = self.client.patch(f"/api/v1/candidates/{candidate_id}", json={
            "request_id": "cand-patch-crud",
            "status": "ignored",
            "confidence": 0.9,
        }).json()
        self.assertEqual(patched["data"]["status"], "ignored")

    def test_similar_candidate_merge_and_terminal_state_not_reopened(self):
        start = datetime.now(TZ) + timedelta(days=8)
        low = candidate_payload("cand-similar-1", "项目会通知第一版", {
            "title": "项目会",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
            "location": "",
            "participants": [],
        }, confidence=0.6)
        high = candidate_payload("cand-similar-2", "项目会通知第二版", {
            "title": "项目会",
            "start_time": (start + timedelta(minutes=5)).isoformat(),
            "end_time": (start + timedelta(minutes=65)).isoformat(),
            "location": "B202",
            "participants": [],
        }, confidence=0.95)
        first = self.client.post("/api/v1/candidates", json=low).json()["data"]["candidate"]
        merged = self.client.post("/api/v1/candidates", json=high).json()["data"]["candidate"]
        self.assertEqual(first["candidate_id"], merged["candidate_id"])
        self.assertEqual(merged["seen_count"], 2)
        self.assertEqual(merged["parsed"]["location"], "B202")

        retry = self.client.post("/api/v1/candidates", json=high).json()["data"]["candidate"]
        self.assertEqual(retry["seen_count"], 2)
        ignored = self.client.patch(f"/api/v1/candidates/{first['candidate_id']}", json={
            "request_id": "cand-similar-ignore",
            "status": "ignored",
        }).json()["data"]
        duplicate = dict(high)
        duplicate["request_id"] = "cand-similar-after-ignore"
        after = self.client.post("/api/v1/candidates", json=duplicate).json()["data"]["candidate"]
        self.assertEqual(after["candidate_id"], ignored["candidate_id"])
        self.assertEqual(after["status"], "ignored")

    def test_candidate_snooze_durations_and_due_query_once(self):
        start = datetime.now(TZ) + timedelta(days=9)
        parsed = {
            "title": "稍后提醒候选",
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        }
        ids = []
        for suffix in ("10", "60", "due"):
            result = self.client.post("/api/v1/candidates", json=candidate_payload(
                f"cand-snooze-{suffix}", f"稍后提醒候选 {suffix}", {**parsed, "title": f"稍后提醒候选 {suffix}"}
            )).json()
            ids.append(result["data"]["candidate"]["candidate_id"])

        before = datetime.now(timezone.utc)
        ten = self.client.post(f"/api/v1/candidates/{ids[0]}/snooze", json={
            "request_id": "cand-snooze-op-10", "duration_minutes": 10,
        }).json()["data"]
        sixty = self.client.post(f"/api/v1/candidates/{ids[1]}/snooze", json={
            "request_id": "cand-snooze-op-60", "duration_minutes": 60,
        }).json()["data"]
        self.assertAlmostEqual((datetime.fromisoformat(ten["snoozed_until"]) - before).total_seconds(), 600, delta=5)
        self.assertAlmostEqual((datetime.fromisoformat(sixty["snoozed_until"]) - before).total_seconds(), 3600, delta=5)

        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.client.post(f"/api/v1/candidates/{ids[2]}/snooze", json={
            "request_id": "cand-snooze-op-due", "snoozed_until": past,
        })
        due_first = self.client.get("/api/v1/candidates", params={"due": "true"}).json()["data"]["candidates"]
        due_second = self.client.get("/api/v1/candidates", params={"due": "true"}).json()["data"]["candidates"]
        self.assertTrue(any(item["candidate_id"] == ids[2] for item in due_first))
        self.assertTrue(next(item for item in due_first if item["candidate_id"] == ids[2])["snooze_notified_at"])
        self.assertFalse(any(item["candidate_id"] == ids[2] for item in due_second))

    def test_create_update_cancel_candidate_confirmation(self):
        start = datetime.now(TZ) + timedelta(days=10)
        create_result = self.client.post("/api/v1/candidates", json=candidate_payload(
            "cand-confirm-create", "创建候选", {
                "title": "候选创建任务",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=1)).isoformat(),
                "location": "C303",
                "participants": [],
            }
        )).json()["data"]["candidate"]
        confirmed_create = self.client.post(
            f"/api/v1/candidates/{create_result['candidate_id']}/confirm",
            json={"request_id": "cand-confirm-create-op"},
        ).json()
        self.assertEqual(confirmed_create["code"], 0)
        task_id = confirmed_create["data"]["task"]["task_id"]
        repeated_create = self.client.post(
            f"/api/v1/candidates/{create_result['candidate_id']}/confirm",
            json={"request_id": "cand-confirm-create-op"},
        ).json()
        self.assertEqual(repeated_create["data"]["task"]["task_id"], task_id)
        self.assertTrue(repeated_create["data"]["idempotent"])

        service = TaskService()
        self.assertTrue(service.mark_reminded(task_id, 30))
        new_start = start + timedelta(hours=2)
        update_candidate = self.client.post("/api/v1/candidates", json=candidate_payload(
            "cand-confirm-update", "候选创建任务推迟到四点", {
                "title": "候选创建任务",
                "start_time": new_start.isoformat(),
                "end_time": (new_start + timedelta(hours=1)).isoformat(),
            },
            intent_type="update",
            target_task_id=task_id,
            changes={"start_time": new_start.isoformat(), "end_time": (new_start + timedelta(hours=1)).isoformat()},
            confidence=0.4,
        )).json()["data"]["candidate"]

        unchanged = self.client.get(f"/api/v1/tasks/{task_id}").json()["data"]
        self.assertEqual(unchanged["start_time"], start.isoformat())
        confirmed_update = self.client.post(
            f"/api/v1/candidates/{update_candidate['candidate_id']}/confirm",
            json={"request_id": "cand-confirm-update-op"},
        ).json()
        self.assertEqual(confirmed_update["data"]["task"]["start_time"], new_start.isoformat())
        self.assertEqual(confirmed_update["data"]["task"]["reminded_offsets"], "[]")
        self.assertEqual(confirmed_update["data"]["task"]["is_reminded"], 0)

        cancel_candidate = self.client.post("/api/v1/candidates", json=candidate_payload(
            "cand-confirm-cancel", "候选创建任务取消", {"title": "候选创建任务"},
            intent_type="cancel", target_task_id=task_id, changes={}, confidence=0.9,
        )).json()["data"]["candidate"]
        before_cancel = self.client.get(f"/api/v1/tasks/{task_id}").json()["data"]
        self.assertNotEqual(before_cancel["status"], "cancelled")
        confirmed_cancel = self.client.post(
            f"/api/v1/candidates/{cancel_candidate['candidate_id']}/confirm",
            json={"request_id": "cand-confirm-cancel-op"},
        ).json()
        self.assertEqual(confirmed_cancel["data"]["task"]["status"], "cancelled")

        duplicate = dict(candidate_payload(
            "cand-confirm-create-duplicate", "创建候选", {
                "title": "候选创建任务",
                "start_time": start.isoformat(),
                "end_time": (start + timedelta(hours=1)).isoformat(),
            }
        ))
        terminal = self.client.post("/api/v1/candidates", json=duplicate).json()["data"]["candidate"]
        self.assertEqual(terminal["candidate_id"], create_result["candidate_id"])
        self.assertEqual(terminal["status"], "confirmed")

    def test_change_hunter_intents_create_candidates_without_direct_mutation(self):
        start = datetime.now(TZ) + timedelta(days=11)
        task_id = self.client.post("/api/v1/tasks", json=task_payload(
            "周会", start, start + timedelta(hours=1), "req-change-hunter-base"
        )).json()["data"]["task_id"]
        cases = [
            ("会议推迟到四点", "update"),
            ("地点改到 302", "update"),
            ("周会取消", "cancel"),
        ]
        for index, (text, expected) in enumerate(cases):
            response = self.client.post("/api/v1/candidates", json=candidate_payload(
                f"cand-change-{index}", text, {
                    "title": "周会",
                    "start_time": start.isoformat(),
                    "end_time": (start + timedelta(hours=1)).isoformat(),
                    "location": "测试地点",
                    "participants": [],
                }, confidence=0.3,
            )).json()["data"]["candidate"]
            self.assertEqual(response["intent_type"], expected)
            self.assertEqual(response["target_task_id"], task_id)
            task = self.client.get(f"/api/v1/tasks/{task_id}").json()["data"]
            self.assertEqual(task["status"], "scheduled")

    def test_free_slots_with_buffer_and_cross_date_boundary(self):
        day = (datetime.now(TZ) + timedelta(days=20)).replace(hour=0, minute=0, second=0, microsecond=0)
        self.client.post("/api/v1/tasks", json=task_payload(
            "占用时段", day.replace(hour=10), day.replace(hour=11), "req-free-busy"
        ))
        completed_id = self.client.post("/api/v1/tasks", json=task_payload(
            "已完成不占用", day.replace(hour=13), day.replace(hour=14), "req-free-completed"
        )).json()["data"]["task_id"]
        self.client.patch(f"/api/v1/tasks/{completed_id}/status", json={"status": "completed"})

        result = self.client.post("/api/v1/tasks/free-slots", json={
            "duration_minutes": 60,
            "range_start": day.replace(hour=9).isoformat(),
            "range_end": (day + timedelta(days=1)).replace(hour=12).isoformat(),
            "working_hours": {"start": "09:00", "end": "18:00"},
            "buffer_minutes": 15,
            "preferred_start": day.replace(hour=10, minute=30).isoformat(),
        }).json()
        self.assertEqual(result["code"], 0)
        suggestions = result["data"]["suggestions"]
        self.assertGreaterEqual(len(suggestions), 3)
        self.assertTrue(all({"start_time", "end_time", "reason"} <= set(item) for item in suggestions))
        for item in suggestions:
            slot_start = datetime.fromisoformat(item["start_time"])
            slot_end = datetime.fromisoformat(item["end_time"])
            self.assertFalse(slot_start < day.replace(hour=11, minute=15) and slot_end > day.replace(hour=9, minute=45))


if __name__ == "__main__":
    unittest.main()
