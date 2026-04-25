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
            created_at TEXT
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

        conn.commit()
        conn.close()

    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn