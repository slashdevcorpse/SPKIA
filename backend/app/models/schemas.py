"""
Pydantic schemas for API requests and responses
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from app.models.database import (
    VerificationStatus,
    AuthenticityLabel,
    C2PAResult,
    SensorPKIResult,
    MLDetectionResult
)


class VerifyFileRequest(BaseModel):
    """Request schema for file upload verification"""
    # File will be handled via multipart form data
    pass


class VerifyURLRequest(BaseModel):
    """Request schema for URL-based verification"""
    url: HttpUrl
    

class VerifyResponse(BaseModel):
    """Response schema for verification initiation"""
    job_id: str
    status: VerificationStatus


class VerificationDetails(BaseModel):
    """Detailed verification results"""
    c2pa: Optional[C2PAResult] = None
    sensor_pki: Optional[SensorPKIResult] = None
    ml_detection: Optional[MLDetectionResult] = None


class VerificationResult(BaseModel):
    """Complete verification result"""
    job_id: str
    status: VerificationStatus
    label: Optional[AuthenticityLabel] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasons: List[str] = []
    details: Optional[VerificationDetails] = None
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DeleteResponse(BaseModel):
    """Response schema for deletion"""
    job_id: str
    deleted: bool
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
    database: str
    ml_models_loaded: bool

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str
    detail: Optional[str] = None
    job_id: Optional[str] = None
