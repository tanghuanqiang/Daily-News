from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./daily_digest.db"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200
    
    # News API
    GNEWS_API_KEY: str = ""
    NEWSDATA_API_KEY: str = ""
    
    # Alibaba Cloud Qwen
    DASHSCOPE_API_KEY: str = ""

    # LLM Configuration
    LLM_PROVIDER: str = "dashscope"  # "dashscope", "ollama", or "nvidia"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:8b"
    
    # NVIDIA GLM API Configuration
    NVIDIA_API_KEY: str = ""  # NVIDIA API Key
    NVIDIA_MODEL: str = "z-ai/glm4.7"  # GLM model name
    
    # Email
    RESEND_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@dailydigest.com"
    
    # SMTP (alternative)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587  # 587 for TLS, 465 for SSL
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    
    # Default email account for sending (if not using Resend)
    DEFAULT_EMAIL_ACCOUNT: str = ""  # 默认发送邮箱账户
    DEFAULT_EMAIL_PASSWORD: str = ""  # 默认发送邮箱密码
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # Scheduler
    DAILY_UPDATE_HOUR: int = 8
    DAILY_UPDATE_MINUTE: int = 0
    TIMEZONE: str = "Asia/Shanghai"
    
    # AI Summary Task Queue
    SUMMARY_TASK_RPM: int = 30              # NVIDIA API max RPM (留10余量给其他请求)
    SUMMARY_TASK_BURST: int = 30            # 突发容量
    SUMMARY_WORKER_INTERVAL: int = 3        # Worker 轮询间隔(秒)
    SUMMARY_MAX_RETRIES: int = 3            # 最大重试次数
    SUMMARY_TASK_CLEANUP_DAYS: int = 7      # 任务清理天数
    
    # Email schedule configuration
    EMAIL_SCHEDULE_TYPE: str = "daily"  # "daily", "weekly", "interval"
    EMAIL_SCHEDULE_HOUR: int = 9  # 邮件发送时间（小时）
    EMAIL_SCHEDULE_MINUTE: int = 0  # 邮件发送时间（分钟）
    EMAIL_SCHEDULE_DAY_OF_WEEK: int = 0  # 每周发送日（0=周一，6=周日）
    EMAIL_SCHEDULE_INTERVAL_HOURS: int = 24  # 间隔发送（小时数）
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()

# Database setup
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_database():
    """Run simple migrations (add columns if missing) for SQLite compatibility.
    Called at startup after Base.metadata.create_all().
    """
    import logging
    _logger = logging.getLogger(__name__)
    try:
        from sqlalchemy import text
        conn = engine.connect()
        
        # Check and add summary_status to news_cache if missing
        try:
            result = conn.execute(text("SELECT summary_status FROM news_cache LIMIT 0"))
            result.close()
            _logger.debug("Migration check: summary_status column already exists")
        except Exception:
            # Column doesn't exist, add it
            conn.execute(text("ALTER TABLE news_cache ADD COLUMN summary_status VARCHAR(20) DEFAULT 'pending'"))
            conn.commit()
            _logger.info("Migration: Added summary_status column to news_cache")
        
        conn.close()
    except Exception as e:
        _logger.warning(f"Database migration skipped: {e}")
