"""
Healthcare Symptom Checker API
AI-powered medical symptom analysis with emergency detection
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.middleware import RateLimitMiddleware, SecurityMiddleware, LoggingMiddleware
from app.routers import symptoms, history
from app.services.rag_service import RAGService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("Starting Healthcare Symptom Checker...")
    
    init_db()
    
    try:
        rag_service = RAGService()
        rag_service.initialize()
        app.state.rag_service = rag_service
        logger.info("RAG service ready")
    except Exception as e:
        logger.error(f"RAG service failed: {e}")
        raise
    
    yield
    
    logger.info("Shutting down...")
    close_db()

app = FastAPI(
    title="Healthcare Symptom Checker API",
    description="AI-powered medical symptom analysis with emergency detection",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware setup (order matters)
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(symptoms.router, prefix="/api/symptom", tags=["symptoms"])
app.include_router(history.router, prefix="/api/history", tags=["history"])

@app.get("/")
async def root():
    return {
        "message": "Healthcare Symptom Checker API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }

@app.get("/api/health")
async def health_check():
    """Check system health and service status"""
    if not hasattr(app.state, 'rag_service'):
        raise HTTPException(status_code=503, detail="RAG service not initialized")
    
    return {
        "status": "healthy",
        "services": {
            "database": "operational",
            "rag": "operational",
            "llm": "operational"
        }
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Handle unexpected errors gracefully"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later.",
            "detail": str(exc) if settings.DEBUG else None
        }
    )

if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable (for Render deployment) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )