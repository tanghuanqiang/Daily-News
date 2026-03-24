"""
Services Module

Additional services for Daily-News application including user profiling,
recommendation algorithms, and analytics.
"""

# 条件导入，避免依赖问题
try:
    from .user_profile_service import UserProfileService, get_user_profile_service
    __all__ = ["UserProfileService", "get_user_profile_service"]
except ImportError:
    # 如果rag模块不存在，跳过导入
    __all__ = []
    pass
