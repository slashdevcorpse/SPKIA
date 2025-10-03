"""
Main verification orchestration service
Coordinates C2PA, Sensor-PKI, and ML detection
"""
import logging
import hashlib
import uuid
from pathlib import Path
from typing import Tuple
from datetime import datetime
import time

from app.models.database import (
    Job,
    ProofData,
    VerificationStatus,
    AuthenticityLabel,
    MetricsData
)
from app.services.c2pa_verifier import c2pa_verifier
from app.services.sensor_pki_verifier import sensor_pki_verifier
from app.services.ml_detector import ml_detector
from app.database import db
from app.config import settings

logger = logging.getLogger(__name__)


class VerificationService:
    """Main verification pipeline orchestrator"""
    
    def __init__(self):
        """Initialize verification service"""
        self.ensemble_threshold = settings.ensemble_threshold
    
    async def create_verification_job(
        self,
        file_path: Path,
        file_type: str
    ) -> Job:
        """
        Create a new verification job
        
        Args:
            file_path: Path to uploaded file
            file_type: MIME type
            
        Returns:
            Job object with job_id
        """
        try:
            # Compute file hash
            file_hash = self._compute_file_hash(file_path)
            file_size = file_path.stat().st_size
            
            # Generate unique job ID
            job_id = str(uuid.uuid4())
            
            # Create job record
            job = Job(
                job_id=job_id,
                file_hash=file_hash,
                file_type=file_type,
                file_size=file_size,
                status=VerificationStatus.PENDING
            )
            
            # Store in database
            job = await db.create_job(job)
            
            logger.info(f"Created verification job: {job_id}")
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to create verification job: {e}", exc_info=True)
            raise
    
    async def process_verification(self, job_id: str, file_path: Path):
        """
        Process verification pipeline
        
        Args:
            job_id: Job identifier
            file_path: Path to file to verify
        """
        start_time = time.time()
        
        try:
            # Update status to processing
            await db.update_job(job_id, status=VerificationStatus.PROCESSING)
            
            logger.info(f"Starting verification for job: {job_id}")
            
            # Step 1: C2PA Verification
            logger.info(f"[{job_id}] Step 1: C2PA verification")
            c2pa_result = await c2pa_verifier.verify(file_path)
            
            # Step 2: Sensor-PKI Verification
            logger.info(f"[{job_id}] Step 2: Sensor-PKI verification")
            sensor_pki_result = await sensor_pki_verifier.verify(file_path)
            
            # Step 3: ML Detection (if no strong cryptographic proof)
            ml_result = None
            if not c2pa_result.valid and not sensor_pki_result.valid:
                logger.info(f"[{job_id}] Step 3: ML detection pipeline")
                try:
                    ml_result = await ml_detector.detect(file_path)
                    logger.info(f"[{job_id}] ML detection completed successfully")
                except Exception as ml_error:
                    logger.error(f"[{job_id}] ML detection failed: {ml_error}", exc_info=True)
                    # Continue with None result - will use UNKNOWN label
            
            # Step 4: Decision logic
            logger.info(f"[{job_id}] Step 4: Decision logic")
            label, confidence, reasons = self._make_decision(
                c2pa_result,
                sensor_pki_result,
                ml_result
            )
            
            # Store proof data
            proof = ProofData(
                job_id=job_id,
                c2pa=c2pa_result,
                sensor_pki=sensor_pki_result,
                ml_detection=ml_result
            )
            await db.create_proof(proof)
            
            # Update job with results
            await db.update_job(
                job_id,
                status=VerificationStatus.COMPLETED,
                label=label,
                confidence=confidence,
                reasons=reasons
            )
            
            # Record metrics
            processing_time_ms = (time.time() - start_time) * 1000
            await self._record_metrics(label, processing_time_ms, c2pa_result, sensor_pki_result)
            
            logger.info(
                f"[{job_id}] Verification completed: {label} "
                f"(confidence: {confidence:.2f}) in {processing_time_ms:.0f}ms"
            )
            
        except Exception as e:
            logger.error(f"Verification failed for job {job_id}: {e}", exc_info=True)
            
            # Update job with error
            await db.update_job(
                job_id,
                status=VerificationStatus.FAILED,
                label=AuthenticityLabel.ERROR,
                error_message=str(e)
            )
    
    def _make_decision(
        self,
        c2pa_result,
        sensor_pki_result,
        ml_result
    ) -> Tuple[AuthenticityLabel, float, list]:
        """
        Ensemble decision logic
        
        Priority:
        1. Sensor-PKI (highest trust)
        2. C2PA (medium trust)
        3. ML Detection (lowest trust, but useful when crypto missing)
        
        Returns:
            Tuple of (label, confidence, reasons)
        """
        reasons = []
        
        # Priority 1: Sensor-PKI
        if sensor_pki_result.valid:
            reasons.append(
                f"Valid sensor-PKI signature from {sensor_pki_result.manufacturer} "
                f"{sensor_pki_result.camera_model}"
            )
            
            # If C2PA also valid, even stronger confidence
            if c2pa_result.valid:
                reasons.append(f"C2PA manifest verified (issuer: {c2pa_result.issuer})")
                confidence = 0.98
            else:
                confidence = 0.95
            
            return AuthenticityLabel.AUTHENTIC_CAMERA, confidence, reasons
        
        # Priority 2: C2PA (but without sensor-PKI)
        if c2pa_result.valid and c2pa_result.trust_chain_valid:
            reasons.append(f"Valid C2PA manifest (issuer: {c2pa_result.issuer})")
            
            if c2pa_result.edit_history:
                reasons.append(f"Edit history: {', '.join(c2pa_result.edit_history[:3])}")
            
            confidence = 0.85  # Lower than sensor-PKI since no hardware proof
            
            return AuthenticityLabel.AUTHENTIC_C2PA, confidence, reasons
        
        # Priority 3: ML Detection
        if ml_result:
            ai_prob = ml_result.ai_probability
            ml_confidence = ml_result.ensemble_confidence
            
            # High AI probability
            if ai_prob >= self.ensemble_threshold:
                reasons.append(
                    f"ML classifiers indicate AI-generated "
                    f"(probability: {ai_prob:.2f})"
                )
                
                if ml_result.detected_generator:
                    reasons.append(f"Detected generator: {ml_result.detected_generator}")
                
                if ml_result.artifacts_found:
                    reasons.extend(ml_result.artifacts_found[:2])
                
                return AuthenticityLabel.LIKELY_AI_GENERATED, ml_confidence, reasons
            
            # Low AI probability suggests real content
            elif ai_prob <= 0.3 and ml_confidence >= 0.7:
                reasons.append(
                    f"ML classifiers suggest authentic content "
                    f"(AI probability: {ai_prob:.2f})"
                )
                reasons.append("Note: No cryptographic proof available")
                
                # Lower confidence since no crypto proof
                return AuthenticityLabel.AUTHENTIC_CAMERA, ml_confidence * 0.6, reasons
        
        # No conclusive evidence
        reasons.append("No cryptographic proofs found")
        
        if ml_result:
            reasons.append(
                f"ML detection inconclusive "
                f"(AI probability: {ml_result.ai_probability:.2f})"
            )
        
        return AuthenticityLabel.UNKNOWN, 0.5, reasons
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA-256 hash of file"""
        hasher = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    async def _record_metrics(
        self,
        label: AuthenticityLabel,
        processing_time_ms: float,
        c2pa_result,
        sensor_pki_result
    ):
        """Record verification metrics"""
        try:
            metrics = MetricsData(
                total_verifications=1,
                authentic_camera_count=1 if label == AuthenticityLabel.AUTHENTIC_CAMERA else 0,
                authentic_c2pa_count=1 if label == AuthenticityLabel.AUTHENTIC_C2PA else 0,
                ai_generated_count=1 if label == AuthenticityLabel.LIKELY_AI_GENERATED else 0,
                unknown_count=1 if label == AuthenticityLabel.UNKNOWN else 0,
                average_processing_time_ms=processing_time_ms,
                c2pa_validation_success_rate=1.0 if c2pa_result.valid else 0.0,
                sensor_pki_validation_success_rate=1.0 if sensor_pki_result.valid else 0.0,
                ml_detection_invocations=1 if not (c2pa_result.valid or sensor_pki_result.valid) else 0
            )
            
            await db.record_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")


# Global verification service instance
verification_service = VerificationService()
