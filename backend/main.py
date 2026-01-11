from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import engine, Base, settings
from routes import auth_router, subscriptions_router, news_router
from routes.schedule import router as schedule_router
from routes.preferences import router as preferences_router
from scheduler import start_scheduler, stop_scheduler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Daily Digest Agent API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    # Start scheduler
    start_scheduler()
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title="Daily Digest Agent API",
    description="Personal news digest application with LLM-powered summaries",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
origins = settings.CORS_ORIGINS.split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(subscriptions_router)
app.include_router(news_router)
app.include_router(schedule_router)
app.include_router(preferences_router)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Daily Digest Agent API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": "2026-01-06"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
