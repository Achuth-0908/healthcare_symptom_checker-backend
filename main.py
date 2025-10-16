"""
Healthcare Symptom Checker API
AI-powered medical symptom analysis with emergency detection
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
import httpx

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.middleware import RateLimitMiddleware, SecurityMiddleware, LoggingMiddleware
from app.routers import symptoms, history
from app.services.enhanced_rag_service import EnhancedRAGService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def keep_alive_ping():
    """Send a GET request to the health endpoint every minute to keep Render alive"""
    while True:
        try:
            # Get the base URL from environment or use localhost for development
            base_url = os.environ.get("RENDER_EXTERNAL_URL", "https://healthcare-symptom-checker.onrender.com")
            if base_url == "http://localhost:4000":
                # For local development, we don't need to ping ourselves
                await asyncio.sleep(60)
                continue
                
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/api/ping", timeout=10.0)
                if response.status_code == 200:
                    logger.info("Keep-alive ping successful")
                else:
                    logger.warning(f"Keep-alive ping failed with status: {response.status_code}")
        except Exception as e:
            logger.error(f"Keep-alive ping error: {e}")
        
        # Wait 60 seconds before next ping
        await asyncio.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown"""
    logger.info("Starting Healthcare Symptom Checker...")
    
    init_db()
    
    try:
        rag_service = EnhancedRAGService()
        rag_service.initialize()
        app.state.rag_service = rag_service
        logger.info("Enhanced RAG service ready with Jina API and medical research")
    except Exception as e:
        logger.error(f"Enhanced RAG service failed: {e}")
        logger.warning("Continuing without Enhanced RAG service - some features may be limited")
        app.state.rag_service = None
    
    # Start the keep-alive background task
    keep_alive_task = asyncio.create_task(keep_alive_ping())
    logger.info("Keep-alive ping task started")
    
    yield
    
    # Cancel the keep-alive task on shutdown
    keep_alive_task.cancel()
    try:
        await keep_alive_task
    except asyncio.CancelledError:
        pass
    
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
# app.add_middleware(SecurityMiddleware)  # Temporarily disabled for CORS fix
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.RATE_LIMIT_REQUESTS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://rag-based-symptom-checker.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:3000",
        "*"  # Allow all origins for now - you can restrict this later
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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

@app.get("/api/ping")
async def ping():
    """Simple ping endpoint for keep-alive services"""
    return {"message": "pong", "timestamp": asyncio.get_event_loop().time()}

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
    
    # Get port from environment variable (for Render deployment) or default to 4000
    port = int(os.environ.get("PORT", 4000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )