"""
SPKIA FastAPI Application
Main entry point for the verification API
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import db
from app.api.routes import router
from app.models.schemas import HealthResponse
from app.services.verification import verification_service

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Taipy integration (optional)
try:
    from app.taipy_integration import create_taipy_router, create_scenario_router
    TAIPY_AVAILABLE = True
except ImportError:
    TAIPY_AVAILABLE = False
    logger.warning("Taipy not available. Scenario management features disabled.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Connect to database
    await db.connect()
    
    # Load ML models
    logger.info("ML models loaded (lazy loading on first request)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await db.disconnect()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Privacy-Preserving Media Authenticity Verification",
    lifespan=lifespan
)

# CORS middleware
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(router, prefix="/api", tags=["verification"])

# Include Taipy routes if available
if TAIPY_AVAILABLE:
    try:
        taipy_router = create_taipy_router(db, verification_service)
        scenario_router = create_scenario_router(db, verification_service)
        app.include_router(taipy_router, prefix="/api")
        app.include_router(scenario_router, prefix="/api")
        logger.info("Taipy integration enabled")
    except Exception as e:
        logger.warning(f"Failed to initialize Taipy integration: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "operational"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        await db.db.command("ping")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"
    
    # Check if ML models are accessible
    ml_models_loaded = True
    try:
        from app.services.ml_detector import ml_detector
        # Models use lazy loading - just check they're importable
        # They'll load on first verification request
        ml_models_loaded = ml_detector is not None
    except Exception as e:
        logger.error(f"ML models health check failed: {e}")
        ml_models_loaded = False
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        database=db_status,
        ml_models_loaded=ml_models_loaded
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.log_level == "DEBUG" else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level=settings.log_level.lower()
    )
