"""
API routes for SPKIA verification service
"""
import logging
from typing import Optional
from pathlib import Path
import tempfile
import aiofiles
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from app.models.schemas import (
    VerifyResponse,
    VerifyURLRequest,
    VerificationResult,
    DeleteResponse,
    VerificationDetails
)
from app.services.verification import verification_service
from app.database import db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/verify", response_model=VerifyResponse)
async def verify_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and verify media file
    
    Returns job_id for polling results
    """
    try:
        # Validate file size
        file_size = 0
        temp_file = None
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            temp_file = Path(tmp.name)
            
            async with aiofiles.open(temp_file, 'wb') as f:
                while chunk := await file.read(8192):
                    file_size += len(chunk)
                    
                    if file_size > settings.max_upload_size_bytes:
                        temp_file.unlink()
                        raise HTTPException(
                            status_code=413,
                            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                        )
                    
                    await f.write(chunk)
        
        # Create verification job
        job = await verification_service.create_verification_job(
            file_path=temp_file,
            file_type=file.content_type or "application/octet-stream"
        )
        
        # Schedule background verification task
        background_tasks.add_task(
            verification_service.process_verification,
            job.job_id,
            temp_file
        )
        
        # Schedule cleanup of temp file
        background_tasks.add_task(_cleanup_temp_file, temp_file)
        
        return VerifyResponse(
            job_id=job.job_id,
            status=job.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify-url", response_model=VerifyResponse)
async def verify_url(
    background_tasks: BackgroundTasks,
    request: VerifyURLRequest
):
    """
    Verify media from URL
    
    Returns job_id for polling results
    """
    try:
        import httpx
        
        # Download file from URL
        async with httpx.AsyncClient() as client:
            response = await client.get(str(request.url), follow_redirects=True)
            response.raise_for_status()
            
            # Check size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > settings.max_upload_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                )
            
            # Save to temp file
            content_type = response.headers.get('content-type', 'application/octet-stream')
            suffix = _guess_extension(content_type)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                temp_file = Path(tmp.name)
                tmp.write(response.content)
        
        # Create verification job
        job = await verification_service.create_verification_job(
            file_path=temp_file,
            file_type=content_type
        )
        
        # Schedule background verification
        background_tasks.add_task(
            verification_service.process_verification,
            job.job_id,
            temp_file
        )
        
        # Schedule cleanup
        background_tasks.add_task(_cleanup_temp_file, temp_file)
        
        return VerifyResponse(
            job_id=job.job_id,
            status=job.status
        )
        
    except httpx.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to download URL: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"URL verification error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/{job_id}", response_model=VerificationResult)
async def get_verification_result(job_id: str):
    """
    Get verification results for a job
    
    Returns current status and results if completed
    """
    try:
        # Get job from database
        job = await db.get_job_by_job_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Build response
        result = VerificationResult(
            job_id=job.job_id,
            status=job.status,
            label=job.label,
            confidence=job.confidence,
            reasons=job.reasons,
            created_at=job.created_at,
            updated_at=job.updated_at,
            error_message=job.error_message
        )
        
        # Add detailed proofs if completed
        if job.status == "completed":
            proof = await db.get_proof(job_id)
            if proof:
                result.details = VerificationDetails(
                    c2pa=proof.c2pa,
                    sensor_pki=proof.sensor_pki,
                    ml_detection=proof.ml_detection
                )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get result error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/verify/{job_id}", response_model=DeleteResponse)
async def delete_verification(job_id: str):
    """
    Force immediate deletion of verification job and data
    
    Respects user's privacy request
    """
    try:
        deleted = await db.delete_job(job_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return DeleteResponse(
            job_id=job_id,
            deleted=True,
            message="Job and associated data deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete job error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_metrics(days: int = 7):
    """
    Get aggregated metrics (anonymized)
    
    Args:
        days: Number of days to aggregate (default: 7)
    """
    try:
        metrics = await db.get_aggregate_metrics(days)
        return JSONResponse(content=metrics)
        
    except Exception as e:
        logger.error(f"Get metrics error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _cleanup_temp_file(file_path: Path):
    """Clean up temporary file"""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to cleanup temp file {file_path}: {e}")


def _guess_extension(content_type: str) -> str:
    """Guess file extension from content type"""
    extensions = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp',
        'video/mp4': '.mp4',
        'video/quicktime': '.mov',
        'video/x-msvideo': '.avi'
    }
    return extensions.get(content_type, '.bin')
