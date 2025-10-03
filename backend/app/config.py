"""
Configuration management using Pydantic settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_workers: int = Field(default=4, env="API_WORKERS")
    secret_key: str = Field(default="change-me-in-production", env="SECRET_KEY")
    
    # Database Configuration
    mongodb_uri: str = Field(default="mongodb://localhost:27017", env="MONGODB_URI")
    mongodb_db_name: str = Field(default="spkia", env="MONGODB_DB_NAME")
    job_ttl_hours: int = Field(default=24, env="JOB_TTL_HOURS")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # Security Configuration
    max_upload_size_mb: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        env="ALLOWED_ORIGINS"
    )
    cors_enabled: bool = Field(default=True, env="CORS_ENABLED")
    
    # ML Model Configuration
    model_path: str = Field(default="/app/models", env="MODEL_PATH")
    ensemble_threshold: float = Field(default=0.7, env="ENSEMBLE_THRESHOLD")
    cnn_model_version: str = Field(default="v1.0", env="CNN_MODEL_VERSION")
    prnu_model_version: str = Field(default="v1.0", env="PRNU_MODEL_VERSION")
    
    # C2PA Configuration
    c2pa_trust_anchors_path: str = Field(
        default="/app/trust_anchors",
        env="C2PA_TRUST_ANCHORS_PATH"
    )
    c2pa_validation_strict: bool = Field(default=True, env="C2PA_VALIDATION_STRICT")
    
    # Sensor-PKI Configuration
    sensor_pki_trust_anchors_path: str = Field(
        default="/app/sensor_pki_anchors",
        env="SENSOR_PKI_TRUST_ANCHORS_PATH"
    )
    sensor_pki_enable: bool = Field(default=True, env="SENSOR_PKI_ENABLE")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    # Application Metadata
    app_name: str = "SPKIA"
    app_version: str = "1.0.0"
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_upload_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
