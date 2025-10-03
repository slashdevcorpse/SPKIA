"""
Integration module for Taipy UI with FastAPI application.
Provides endpoint for launching Taipy GUI alongside REST API.
"""
import asyncio
import threading
from typing import Optional
import logging

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse

from app.taipy_ui import create_taipy_ui, SPKIATaipyUI
from app.database import Database
from app.services.verification import VerificationService

logger = logging.getLogger(__name__)

# Global Taipy UI instance
_taipy_ui_instance: Optional[SPKIATaipyUI] = None
_taipy_thread: Optional[threading.Thread] = None


def create_taipy_router(db: Database, verification_service: VerificationService) -> APIRouter:
    """
    Create FastAPI router for Taipy integration endpoints.
    
    Args:
        db: Database instance
        verification_service: Verification service instance
    
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/taipy", tags=["Taipy UI"])
    
    @router.post("/start")
    async def start_taipy_ui(background_tasks: BackgroundTasks):
        """
        Start Taipy GUI application in a background thread.
        Taipy UI will be available at http://localhost:5000
        """
        global _taipy_ui_instance, _taipy_thread
        
        if _taipy_thread and _taipy_thread.is_alive():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "already_running",
                    "message": "Taipy UI is already running",
                    "url": "http://localhost:5000"
                }
            )
        
        try:
            # Create Taipy UI instance
            _taipy_ui_instance = await create_taipy_ui(db, verification_service)
            
            # Start Taipy in a separate thread
            def run_taipy():
                try:
                    logger.info("Starting Taipy UI on port 5000...")
                    _taipy_ui_instance.run(host="0.0.0.0", port=5000, debug=False)
                except Exception as e:
                    logger.error(f"Taipy UI error: {e}", exc_info=True)
            
            _taipy_thread = threading.Thread(target=run_taipy, daemon=True)
            _taipy_thread.start()
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "started",
                    "message": "Taipy UI started successfully",
                    "url": "http://localhost:5000"
                }
            )
        except Exception as e:
            logger.error(f"Failed to start Taipy UI: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"Failed to start Taipy UI: {str(e)}"
                }
            )
    
    @router.get("/status")
    async def get_taipy_status():
        """
        Check if Taipy UI is running.
        """
        global _taipy_thread
        
        if _taipy_thread and _taipy_thread.is_alive():
            return JSONResponse(
                status_code=200,
                content={
                    "status": "running",
                    "url": "http://localhost:5000"
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "stopped",
                    "message": "Taipy UI is not running. Use POST /taipy/start to start it."
                }
            )
    
    @router.post("/stop")
    async def stop_taipy_ui():
        """
        Stop Taipy GUI application.
        Note: Due to threading limitations, this may not fully stop the GUI.
        Restart the main application to completely stop Taipy.
        """
        global _taipy_thread
        
        if _taipy_thread and _taipy_thread.is_alive():
            # Note: Python threads cannot be forcefully stopped
            # The Taipy GUI server would need to be stopped from within
            return JSONResponse(
                status_code=200,
                content={
                    "status": "warning",
                    "message": "Taipy UI cannot be stopped programmatically. Restart the application to stop it."
                }
            )
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "not_running",
                    "message": "Taipy UI is not running"
                }
            )
    
    return router


# Add scenario management endpoints
def create_scenario_router(db: Database, verification_service: VerificationService) -> APIRouter:
    """
    Create FastAPI router for threshold scenario management.
    Allows programmatic access to scenario features without Taipy GUI.
    
    Args:
        db: Database instance
        verification_service: Verification service instance
    
    Returns:
        Configured APIRouter
    """
    from app.taipy_ui import ThresholdScenarioManager
    from pydantic import BaseModel, Field
    from typing import List
    
    # Initialize scenario manager
    scenario_manager = ThresholdScenarioManager(db, verification_service)
    
    router = APIRouter(prefix="/scenarios", tags=["Threshold Scenarios"])
    
    # Request models
    class CreateScenarioRequest(BaseModel):
        name: str = Field(..., description="Scenario name")
        description: str = Field(default="", description="Scenario description")
        ensemble_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Ensemble threshold")
        cnn_weight: float = Field(default=0.4, ge=0.0, le=1.0, description="CNN weight")
        prnu_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="PRNU weight")
        metadata_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Metadata weight")
        min_confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum confidence")
    
    class CompareScenariosRequest(BaseModel):
        scenario_ids: List[str] = Field(..., description="List of scenario IDs to compare")
        verification_sample: Optional[List[str]] = Field(None, description="Optional job IDs to analyze")
    
    @router.post("/create")
    async def create_scenario(request: CreateScenarioRequest):
        """
        Create a new threshold scenario for what-if analysis.
        """
        try:
            scenario_id = await scenario_manager.create_scenario(
                name=request.name,
                description=request.description,
                ensemble_threshold=request.ensemble_threshold,
                cnn_weight=request.cnn_weight,
                prnu_weight=request.prnu_weight,
                metadata_weight=request.metadata_weight,
                min_confidence=request.min_confidence
            )
            
            scenario = scenario_manager.get_scenario(scenario_id)
            
            return JSONResponse(
                status_code=201,
                content={
                    "status": "success",
                    "scenario": scenario
                }
            )
        except Exception as e:
            logger.error(f"Failed to create scenario: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)}
            )
    
    @router.get("/list")
    async def list_scenarios():
        """
        List all available threshold scenarios.
        """
        scenarios = scenario_manager.list_scenarios()
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "count": len(scenarios),
                "scenarios": scenarios
            }
        )
    
    @router.get("/{scenario_id}")
    async def get_scenario(scenario_id: str):
        """
        Get details of a specific scenario.
        """
        scenario = scenario_manager.get_scenario(scenario_id)
        
        if not scenario:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Scenario not found"}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "scenario": scenario
            }
        )
    
    @router.delete("/{scenario_id}")
    async def delete_scenario(scenario_id: str):
        """
        Delete a threshold scenario.
        """
        success = scenario_manager.delete_scenario(scenario_id)
        
        if not success:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Scenario not found"}
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"Scenario {scenario_id} deleted successfully"
            }
        )
    
    @router.post("/compare")
    async def compare_scenarios(request: CompareScenariosRequest):
        """
        Compare multiple threshold scenarios side-by-side.
        """
        try:
            results = await scenario_manager.compare_scenarios(
                scenario_ids=request.scenario_ids,
                verification_sample=request.verification_sample
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "comparison": results
                }
            )
        except Exception as e:
            logger.error(f"Failed to compare scenarios: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": str(e)}
            )
    
    return router
