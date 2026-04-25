from pydantic_settings import BaseSettings
from typing import List, Optional, Dict
from pathlib import Path

class Settings(BaseSettings):
    # ========== 日志相关（必选，解决logger.py所有报错） ==========
    DEBUG: bool = True
    DEFAULT_TIMEZONE: str = "Asia/Shanghai"
    LOG_LEVEL: str = "INFO"          # 日志级别
    LOG_FILE: Path = Path(__file__).parent.parent.parent / "logs" / "app.log"  # 日志文件路径
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # 补充日志格式（潜在缺失）

    # ========== 数据库相关（必选） ==========
    DB_PATH: Path = Path(__file__).parent.parent.parent / "data" / "schedule.db"  # 数据库文件路径
    database_url: str = "sqlite:///./schedule.db"  # 兼容原有字段

    DEFAULT_DURATION_MINUTES: int = 60
    BLUELM_API_KEY: Optional[str] = "sk-xuanji-2026488951-bFFoZkRVUGZpV0ZMeFFpaQ=="
    BLUELM_API_URL: Optional[str] = "https://aigc.vivo.com/api/blueLM"
    BLUELM_TIMEOUT: int = 30

    # ========== 通用配置（兼容原有字段） ==========
    api_key: Optional[str] = None  # 兼容原有多余字段
    cors_origins: str = "http://localhost:5173,http://localhost:8080"  # 跨域配置
    APP_HOST: str = "127.0.0.1"  # 补充服务地址（潜在缺失）
    APP_PORT: int = 8000         # 补充服务端口（潜在缺失）

    class Config:
        env_file = ".env"                # 读取.env文件
        env_file_encoding = "utf-8"      # 编码格式
        extra = "ignore"                 # 关键：忽略.env中未定义的字段（彻底解决extra_forbidden报错）

# 确保目录存在（日志+数据库）
settings = Settings()
# 数据库目录
settings.DB_PATH.parent.mkdir(exist_ok=True, parents=True)
# 日志目录
settings.LOG_FILE.parent.mkdir(exist_ok=True, parents=True)
