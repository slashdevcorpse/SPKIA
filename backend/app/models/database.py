"""
Database models for MongoDB collections
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic v2"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, validation_info=None):
        """Validate ObjectId (Pydantic v2 compatible)"""
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class VerificationStatus(str, Enum):
    """Job status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AuthenticityLabel(str, Enum):
    """Authenticity classification labels"""
    AUTHENTIC_CAMERA = "authentic_camera"
    AUTHENTIC_C2PA = "authentic_c2pa"
    LIKELY_AI_GENERATED = "likely_ai_generated"
    UNKNOWN = "unknown"
    ERROR = "error"


class C2PAResult(BaseModel):
    """C2PA verification result"""
    valid: bool
    issuer: Optional[str] = None
    trust_chain_valid: bool = False
    manifest_store: Optional[Dict[str, Any]] = None
    edit_history: Optional[List[str]] = None
    error: Optional[str] = None


class SensorPKIResult(BaseModel):
    """Sensor-PKI verification result"""
    valid: bool
    manufacturer: Optional[str] = None
    camera_model: Optional[str] = None
    sensor_id: Optional[str] = None
    signature_algorithm: Optional[str] = None
    public_key_fingerprint: Optional[str] = None
    error: Optional[str] = None


class MLDetectionResult(BaseModel):
    """ML-based detection result"""
    ai_probability: float = Field(ge=0.0, le=1.0)
    cnn_score: Optional[float] = None
    prnu_score: Optional[float] = None
    metadata_anomaly_score: Optional[float] = None
    transformer_score: Optional[float] = None
    ensemble_confidence: float = Field(ge=0.0, le=1.0)
    detected_generator: Optional[str] = None
    artifacts_found: List[str] = []


class ProofData(BaseModel):
    """Cryptographic and ML proof data"""
    job_id: str
    c2pa: Optional[C2PAResult] = None
    sensor_pki: Optional[SensorPKIResult] = None
    ml_detection: Optional[MLDetectionResult] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Job(BaseModel):
    """Verification job model"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    job_id: str = Field(..., unique=True)
    file_hash: str
    file_type: str
    file_size: int
    status: VerificationStatus = VerificationStatus.PENDING
    label: Optional[AuthenticityLabel] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    reasons: List[str] = []
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }


class MetricsData(BaseModel):
    """Aggregated metrics for monitoring"""
    date: datetime = Field(default_factory=datetime.utcnow)
    total_verifications: int = 0
    authentic_camera_count: int = 0
    authentic_c2pa_count: int = 0
    ai_generated_count: int = 0
    unknown_count: int = 0
    average_processing_time_ms: float = 0.0
    c2pa_validation_success_rate: float = 0.0
    sensor_pki_validation_success_rate: float = 0.0
    ml_detection_invocations: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
