# Routes package initialization
from .auth import router as auth_router
from .subscriptions import router as subscriptions_router
from .news import router as news_router

__all__ = ["auth_router", "subscriptions_router", "news_router"]
