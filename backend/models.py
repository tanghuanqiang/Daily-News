from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, UniqueConstraint, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=True)
    
    # 用户级别的邮件定时配置
    email_schedule_enabled = Column(Boolean, default=False)  # 是否启用定时邮件
    email_schedule_type = Column(String, default="daily")  # "daily", "weekly", "interval"
    email_schedule_hour = Column(Integer, default=9)  # 发送时间（小时）
    email_schedule_minute = Column(Integer, default=0)  # 发送时间（分钟）
    email_schedule_day_of_week = Column(Integer, default=0)  # 每周发送日（0=周一，6=周日）
    email_schedule_interval_hours = Column(Integer, default=24)  # 间隔小时数
    last_email_sent_at = Column(DateTime, nullable=True)  # 上次发送邮件的时间
    
    # 登录相关
    last_login = Column(DateTime, nullable=True)  # 上次登录时间
    
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


class CustomRSSFeed(Base):
    """自定义RSS源表"""
    __tablename__ = "custom_rss_feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    topic = Column(String, nullable=False)  # 主题名称
    feed_url = Column(String, nullable=False)  # RSS源URL
    is_active = Column(Boolean, default=True)  # 是否启用（是否订阅）
    roast_mode = Column(Boolean, default=False)  # 是否使用吐槽模式
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")


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
    
    # Unique identifier for RSS entries (feed_url + guid/link hash)
    entry_id = Column(String, index=True, unique=True, nullable=True)  # 用于RSS源的唯一标识
    
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


class NewsFeedback(Base):
    """新闻反馈表 - 存储用户对新闻摘要的反馈"""
    __tablename__ = "news_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    news_id = Column(Integer, ForeignKey("news_cache.id"), nullable=False, index=True)
    feedback_type = Column(String(20), nullable=False)  # 'like', 'dislike', 'share'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 唯一约束：每个用户对每条新闻的每种反馈类型只能有一条记录
    __table_args__ = (
        UniqueConstraint('user_id', 'news_id', 'feedback_type', name='uq_user_news_feedback'),
    )


class UserActivityLog(Base):
    """用户行为日志表 - 追踪用户活跃时间用于推送优化"""
    __tablename__ = "user_activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    activity_type = Column(String(50), nullable=False, index=True)  # login, read, share, feedback, email_open
    activity_time = Column(DateTime, default=datetime.utcnow, index=True)
    hour_of_day = Column(Integer, nullable=False, index=True)  # 0-23, 用于快速分析
    day_of_week = Column(Integer, nullable=False, index=True)  # 0-6 (周一到周日)
    extra_data = Column(JSON, default=dict)  # 额外信息（如新闻ID、分享平台等）
    
    # 索引优化
    __table_args__ = (
        Index('idx_user_activity_time', 'user_id', 'activity_time'),
        Index('idx_user_activity_type_hour', 'user_id', 'activity_type', 'hour_of_day'),
    )


class AchievementDefinition(Base):
    """成就定义表 - 定义所有可用的成就"""
    __tablename__ = "achievement_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False)  # 唯一标识，如 'first_read', '7_days_streak'
    name = Column(String(100), nullable=False)  # 成就名称，如 "连续阅读7天"
    description = Column(Text, nullable=False)  # 成就描述
    icon = Column(String(50), nullable=True)  # 图标（emoji或图标名称）
    category = Column(String(50), nullable=True)  # 类别：'reading', 'exploration', 'early_bird', 'sharing'
    requirement_config = Column(JSON, default=dict)  # 解锁条件配置，如 {'days': 7, 'count': 10}
    points = Column(Integer, default=0)  # 成就点数
    is_active = Column(Boolean, default=True)  # 是否启用
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserAchievement(Base):
    """用户成就表 - 记录用户获得的成就"""
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievement_definitions.id"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    progress_data = Column(JSON, default=dict)  # 解锁时的进度数据快照
    
    # 唯一约束：每个用户只能获得每个成就一次
    __table_args__ = (
        UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )


class VectorIndexStatus(Base):
    """向量索引状态表 - 跟踪新闻向量索引的构建状态"""
    __tablename__ = "vector_index_status"
    
    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, ForeignKey("news_cache.id"), nullable=False, unique=True, index=True)
    is_indexed = Column(Boolean, default=False)  # 是否已构建向量索引
    indexed_at = Column(DateTime, nullable=True)  # 索引构建时间
    embedding_version = Column(String, nullable=True)  # Embedding模型版本
    vector_id = Column(String, nullable=True)  # ChromaDB中的向量ID
    index_attempts = Column(Integer, default=0)  # 索引尝试次数
    last_error = Column(Text, nullable=True)  # 最后一次错误信息
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Experiment(Base):
    """实验配置表 - 定义A/B测试实验"""
    __tablename__ = "experiments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 实验名称（唯一）
    description = Column(Text, nullable=True)  # 实验描述
    status = Column(String(20), default="draft")  # 状态: draft, running, paused, completed
    traffic_allocation = Column(Float, default=1.0)  # 流量分配（0-1，占总流量的比例）
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 创建者ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)  # 实验开始时间
    completed_at = Column(DateTime, nullable=True)  # 实验完成时间
    
    # 唯一约束：实验名称唯一
    __table_args__ = (
        UniqueConstraint('name', name='uq_experiment_name'),
    )


class ExperimentVariant(Base):
    """实验版本表 - 存储实验的不同版本配置"""
    __tablename__ = "experiment_variants"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    name = Column(String(50), nullable=False)  # 版本名称（如 "control", "treatment"）
    description = Column(Text, nullable=True)  # 版本描述
    traffic_weight = Column(Float, nullable=False)  # 流量权重（该版本占总实验流量的比例）
    config = Column(JSON, default=dict)  # 版本配置（JSON格式，包含UI、文案等）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一约束：同一实验下版本名称唯一
    __table_args__ = (
        UniqueConstraint('experiment_id', 'name', name='uq_experiment_variant'),
    )


class UserExperimentAssignment(Base):
    """用户实验分配表 - 记录用户被分配到哪个实验版本"""
    __tablename__ = "user_experiment_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("experiment_variants.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)  # 分配时间
    
    # 唯一约束：同一用户在同一实验中只能分配到一个版本
    __table_args__ = (
        UniqueConstraint('user_id', 'experiment_id', name='uq_user_experiment_assignment'),
    )


class ExperimentResult(Base):
    """实验结果表 - 存储实验的统计结果"""
    __tablename__ = "experiment_results"
    
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("experiment_variants.id"), nullable=False, index=True)
    metric_name = Column(String(50), nullable=False, index=True)  # 指标名称（如 "click_rate", "conversion_rate"）
    metric_value = Column(Float, nullable=False)  # 指标值
    sample_size = Column(Integer, default=0)  # 样本量
    calculated_at = Column(DateTime, default=datetime.utcnow)  # 计算时间
    
    # 索引优化
    __table_args__ = (
        Index('idx_experiment_metric', 'experiment_id', 'metric_name'),
        Index('idx_variant_metric', 'variant_id', 'metric_name'),
    )


class ExperimentEvent(Base):
    """实验事件表 - 记录用户在实验中的行为事件"""
    __tablename__ = "experiment_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)
    variant_id = Column(Integer, ForeignKey("experiment_variants.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # 事件类型（如 "view", "click", "conversion"）
    event_data = Column(JSON, default=dict)  # 事件数据
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 索引优化
    __table_args__ = (
        Index('idx_user_experiment_event', 'user_id', 'experiment_id', 'event_type'),
        Index('idx_variant_event', 'variant_id', 'event_type'),
    )


class InvitationCode(Base):
    """邀请码表 - 存储邀请码和邀请关系"""
    __tablename__ = "invitation_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)  # 邀请码（6-8位字符）
    generated_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)  # 创建用户ID
    is_used = Column(Boolean, default=False)  # 是否已被使用
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 使用用户ID（注册时）
    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)  # 使用时间
    
    # 唯一约束：每个邀请码唯一
    __table_args__ = (
        UniqueConstraint('code', name='uq_invitation_code'),
    )


class UserInvitationStats(Base):
    """用户邀请统计表 - 记录用户的邀请统计数据"""
    __tablename__ = "user_invitation_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)  # 用户ID
    total_invited = Column(Integer, default=0)  # 总邀请人数（生成的邀请码数量）
    successful_invites = Column(Integer, default=0)  # 成功邀请数（被使用的邀请码数量）
    total_points_earned = Column(Integer, default=0)  # 获得的总成就点数
    last_invited_at = Column(DateTime, nullable=True)  # 最后邀请时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一约束：每个用户只有一条统计记录
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_invitation_stats'),
    )


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
    username: Optional[str] = None
    is_admin: bool
    is_active: bool
    email_notifications: bool
    email_verified: bool
    created_at: dt
    last_login: Optional[dt] = None
    
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


class CustomRSSFeedCreate(BaseModel):
    topic: str
    feed_url: str


class CustomRSSFeedUpdate(BaseModel):
    is_active: Optional[bool] = None
    roast_mode: Optional[bool] = None


class CustomRSSFeedResponse(BaseModel):
    id: int
    topic: str
    feed_url: str
    is_active: bool
    roast_mode: bool
    created_at: dt
    
    class Config:
        from_attributes = True


# P1: 反馈、分享和成就相关的Pydantic schemas
class NewsFeedbackCreate(BaseModel):
    news_id: int
    feedback_type: str  # 'like', 'dislike', 'share'


class NewsFeedbackResponse(BaseModel):
    id: int
    user_id: int
    news_id: int
    feedback_type: str
    created_at: dt
    
    class Config:
        from_attributes = True


class AchievementDefinitionCreate(BaseModel):
    code: str
    name: str
    description: str
    icon: Optional[str] = None
    category: Optional[str] = None
    requirement_config: dict = {}
    points: int = 0


class AchievementDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    icon: Optional[str]
    category: Optional[str]
    requirement_config: dict
    points: int
    is_active: bool
    
    class Config:
        from_attributes = True


class UserAchievementResponse(BaseModel):
    id: int
    user_id: int
    achievement_id: int
    unlocked_at: dt
    progress_data: dict
    
    class Config:
        from_attributes = True


class AchievementWithProgress(BaseModel):
    # 扁平化结构，直接包含成就定义的所有字段
    id: int
    code: str
    name: str
    description: str
    icon: Optional[str]
    category: Optional[str]
    points: int
    is_unlocked: bool
    unlocked_at: Optional[dt] = None
    progress: float  # 0.0 - 1.0
    current_value: int
    requirement_value: int
    
    class Config:
        from_attributes = True


class ShareTemplateResponse(BaseModel):
    text: str
    url: str
    platform: str
    
    class Config:
        from_attributes = True


# P2: 邀请系统相关的Pydantic schemas
class InvitationCodeResponse(BaseModel):
    id: int
    code: str
    generated_by: int
    is_used: bool
    used_by: Optional[int]
    created_at: dt
    used_at: Optional[dt]
    
    class Config:
        from_attributes = True


class InvitationStatsResponse(BaseModel):
    total_invited: int
    successful_invites: int
    total_points_earned: int
    last_invited_at: Optional[dt]
    invite_success_rate: float  # 邀请成功率（百分比）
    
    class Config:
        from_attributes = True


class InvitationRewardResponse(BaseModel):
    invitation_code: str
    inviter_points: int  # 邀请人获得的点数
    invitee_points: int  # 被邀请人获得的点数
    message: str
    
    class Config:
        from_attributes = True


class InviteClaimRequest(BaseModel):
    invitation_code: str
    
    class Config:
        from_attributes = True


# P2: A/B测试平台相关的Pydantic schemas
class ExperimentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    traffic_allocation: float = 1.0


class ExperimentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: str
    traffic_allocation: float
    created_by: int
    created_at: dt
    updated_at: dt
    started_at: Optional[dt]
    completed_at: Optional[dt]
    
    class Config:
        from_attributes = True


class ExperimentVariantCreate(BaseModel):
    experiment_id: int
    name: str
    description: Optional[str] = None
    traffic_weight: float
    config: dict = {}


class ExperimentVariantResponse(BaseModel):
    id: int
    experiment_id: int
    name: str
    description: Optional[str]
    traffic_weight: float
    config: dict
    created_at: dt
    updated_at: dt
    
    class Config:
        from_attributes = True


class ExperimentAssignmentResponse(BaseModel):
    user_id: int
    experiment_id: int
    variant_id: int
    variant_name: str
    variant_config: dict
    assigned_at: dt
    
    class Config:
        from_attributes = True


class ExperimentEventCreate(BaseModel):
    experiment_id: int
    event_type: str
    event_data: dict = {}


class ExperimentResultResponse(BaseModel):
    experiment_id: int
    variant_id: int
    variant_name: str
    metric_name: str
    metric_value: float
    sample_size: int
    calculated_at: dt
    
    class Config:
        from_attributes = True


class ExperimentReport(BaseModel):
    experiment: ExperimentResponse
    variants: List[ExperimentVariantResponse]
    results: List[ExperimentResultResponse]
    total_users: int
    significance: Optional[float]  # p-value
    
    class Config:
        from_attributes = True
