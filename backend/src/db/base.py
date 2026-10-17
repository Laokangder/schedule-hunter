import sqlite3
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("db")

class DBConnection:
    def __init__(self):
        self.db_path = settings.DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建任务表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            request_id TEXT UNIQUE,
            title TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            location TEXT,
            participants TEXT,
            priority TEXT DEFAULT 'normal',
            reminder_policy TEXT,
            source_text TEXT,
            input_type TEXT,
            status TEXT DEFAULT 'scheduled',
            is_reminded INTEGER DEFAULT 0,
            reminded_offsets TEXT DEFAULT '[]',
            created_at TEXT
        )
        ''')

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN request_id TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN is_reminded INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN reminded_offsets TEXT DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN source_text TEXT")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN status TEXT DEFAULT 'pending'")
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT")
        except sqlite3.OperationalError:
            pass

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            candidate_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL UNIQUE,
            dedup_key TEXT NOT NULL,
            intent_type TEXT NOT NULL DEFAULT 'create',
            target_task_id TEXT,
            source_type TEXT NOT NULL DEFAULT 'manual',
            source_package TEXT,
            source_app_name TEXT,
            source_text TEXT NOT NULL,
            parsed TEXT NOT NULL DEFAULT '{}',
            changes TEXT NOT NULL DEFAULT '{}',
            confidence REAL NOT NULL DEFAULT 0,
            match_confidence REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            snoozed_until TEXT,
            snooze_notified_at TEXT,
            seen_count INTEGER NOT NULL DEFAULT 1,
            sources TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS idempotency_operations (
            request_id TEXT PRIMARY KEY,
            operation TEXT NOT NULL,
            response_data TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_requests (
            request_id TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_dedup_keys (
            dedup_key TEXT PRIMARY KEY,
            candidate_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')

        # 创建日志表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS request_logs (
            trace_id TEXT PRIMARY KEY,
            request_id TEXT,
            request_type TEXT,
            status_code INTEGER,
            created_at TEXT
        )
        ''')

        # 创建索引（提升按日期查询性能）
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_start_time ON tasks(start_time)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_tasks_request_id ON tasks(request_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidates_status_updated
        ON candidates(status, updated_at)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidates_dedup_key
        ON candidates(dedup_key)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidates_similarity
        ON candidates(status, intent_type)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidates_snoozed_due
        ON candidates(status, snoozed_until, snooze_notified_at)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidate_requests_candidate
        ON candidate_requests(candidate_id)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_candidate_dedup_candidate
        ON candidate_dedup_keys(candidate_id)
        ''')

        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
