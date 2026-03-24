# Routes package initialization
from .auth import router as auth_router
from .subscriptions import router as subscriptions_router
from .news import router as news_router
from .feedback import router as feedback_router
from .sharing import router as sharing_router
from .achievements import router as achievements_router
from .experiments import router as experiments_router
from .invitations import router as invitations_router
from .admin import router as admin_router

__all__ = [
    "auth_router",
    "subscriptions_router",
    "news_router",
    "feedback_router",
    "sharing_router",
    "achievements_router",
    "experiments_router",
    "invitations_router",
    "admin_router"
]
