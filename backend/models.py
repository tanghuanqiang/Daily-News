from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=True)
    
    # 用户级别的邮件定时配置
    email_schedule_enabled = Column(Boolean, default=False)  # 是否启用定时邮件
    email_schedule_type = Column(String, default="daily")  # "daily", "weekly", "interval"
    email_schedule_hour = Column(Integer, default=9)  # 发送时间（小时）
    email_schedule_minute = Column(Integer, default=0)  # 发送时间（分钟）
    email_schedule_day_of_week = Column(Integer, default=0)  # 每周发送日（0=周一，6=周日）
    email_schedule_interval_hours = Column(Integer, default=24)  # 间隔小时数
    last_email_sent_at = Column(DateTime, nullable=True)  # 上次发送邮件的时间
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String, nullable=False)  # e.g., "AI", "科技", "财经"
    roast_mode = Column(Boolean, default=False)  # 吐槽模式
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")


class NewsCache(Base):
    __tablename__ = "news_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True, nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)  # LLM generated summary
    summary_roast = Column(Text, nullable=True)  # 吐槽模式摘要
    url = Column(String, nullable=False)
    source = Column(String, nullable=True)  # News source name
    image_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    date = Column(String, index=True)  # YYYY-MM-DD for daily grouping
    relevance_score = Column(Float, nullable=True, default=0.5)  # 相关性分数 (0-1)，由LLM评估
    
    # Metadata
    raw_content = Column(Text, nullable=True)  # Original news content snippet


class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(String, nullable=False)  # "fetch", "summarize", "email", "error"
    message = Column(Text, nullable=False)
    log_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    verification_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TopicRefreshStatus(Base):
    """主题刷新状态表 - 用于跟踪主题刷新状态，避免重复刷新"""
    __tablename__ = "topic_refresh_status"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # YYYY-MM-DD
    last_refreshed_at = Column(DateTime, nullable=True)
    is_refreshing = Column(Boolean, default=False)
    refresh_lock_id = Column(String, nullable=True)  # 锁标识，用于防并发
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一约束：每个主题+日期只有一个状态记录
    __table_args__ = (
        UniqueConstraint('topic', 'date', name='uq_topic_date'),
    )


class UserNewsInteraction(Base):
    """用户新闻交互记录表 - 记录用户对新闻的阅读状态"""
    __tablename__ = "user_news_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    news_id = Column(Integer, ForeignKey("news_cache.id"), nullable=False, index=True)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserPreference(Base):
    """用户偏好设置表"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    hide_read = Column(Boolean, default=False)  # 是否隐藏已读新闻
    sort_by = Column(String, default="time")  # 排序方式："time"（时间）或 "relevance"（相关性）
    hidden_sources = Column(JSON, default=list)  # 隐藏的新闻来源列表
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic schemas for API
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime as dt


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    email_notifications: bool
    created_at: dt
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class SubscriptionCreate(BaseModel):
    topic: str
    roast_mode: bool = False


class SubscriptionUpdate(BaseModel):
    roast_mode: Optional[bool] = None
    is_active: Optional[bool] = None


class SubscriptionResponse(BaseModel):
    id: int
    topic: str
    roast_mode: bool
    is_active: bool
    created_at: dt
    
    class Config:
        from_attributes = True


class NewsItem(BaseModel):
    id: int
    topic: str
    title: str
    summary: str
    summary_roast: Optional[str]
    url: str
    source: Optional[str]
    image_url: Optional[str]
    published_at: Optional[dt]
    fetched_at: dt
    date: str
    
    class Config:
        from_attributes = True


class NewsSummary(BaseModel):
    topic: str
    news_items: List[NewsItem]
    last_updated: dt
    roast_mode: bool = False


class DashboardResponse(BaseModel):
    topics: List[NewsSummary]
    last_global_update: Optional[dt]


class UserPreferenceResponse(BaseModel):
    hide_read: bool
    sort_by: str
    hidden_sources: List[str]
    
    class Config:
        from_attributes = True


class UserPreferenceUpdate(BaseModel):
    hide_read: Optional[bool] = None
    sort_by: Optional[str] = None
    hidden_sources: Optional[List[str]] = None
