"""
Services Module

Additional services for Daily-News application including user profiling,
recommendation algorithms, and analytics.
"""

from .user_profile_service import UserProfileService, get_user_profile_service

__all__ = ["UserProfileService", "get_user_profile_service"]
