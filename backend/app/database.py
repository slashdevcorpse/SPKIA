"""
Database connection and operations
"""
import logging
from typing import Optional, List
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING
from pymongo.errors import DuplicateKeyError

from app.config import settings
from app.models.database import Job, ProofData, MetricsData, VerificationStatus

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database manager"""
    
    def __init__(self):
        """Initialize database connection"""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB and setup indexes"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_db_name]
            
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {settings.mongodb_db_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes including TTL"""
        try:
            # Jobs collection indexes
            jobs_indexes = [
                IndexModel([("job_id", ASCENDING)], unique=True),
                IndexModel([("file_hash", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel(
                    [("expires_at", ASCENDING)],
                    expireAfterSeconds=0  # TTL index
                ),
                IndexModel([("created_at", ASCENDING)])
            ]
            await self.db.jobs.create_indexes(jobs_indexes)
            
            # Proofs collection indexes
            proofs_indexes = [
                IndexModel([("job_id", ASCENDING)], unique=True),
                IndexModel(
                    [("created_at", ASCENDING)],
                    expireAfterSeconds=settings.job_ttl_hours * 3600
                )
            ]
            await self.db.proofs.create_indexes(proofs_indexes)
            
            # Metrics collection indexes
            metrics_indexes = [
                IndexModel([("date", ASCENDING)]),
                IndexModel(
                    [("date", ASCENDING)],
                    expireAfterSeconds=30 * 24 * 3600  # Keep metrics for 30 days
                )
            ]
            await self.db.metrics.create_indexes(metrics_indexes)
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    async def create_job(self, job: Job) -> Job:
        """Create a new verification job"""
        try:
            job_dict = job.model_dump(by_alias=True, exclude={'id'})
            result = await self.db.jobs.insert_one(job_dict)
            job.id = result.inserted_id
            return job
            
        except DuplicateKeyError:
            # Job with same job_id already exists
            existing_job = await self.get_job_by_job_id(job.job_id)
            if existing_job:
                return existing_job
            raise
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise
    
    async def get_job_by_job_id(self, job_id: str) -> Optional[Job]:
        """Get job by job_id"""
        try:
            job_dict = await self.db.jobs.find_one({"job_id": job_id})
            if job_dict:
                return Job(**job_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get job: {e}")
            return None
    
    async def update_job(
        self,
        job_id: str,
        status: Optional[VerificationStatus] = None,
        **kwargs
    ) -> bool:
        """Update job fields"""
        try:
            update_dict = {"updated_at": datetime.utcnow()}
            
            if status:
                update_dict["status"] = status
            
            update_dict.update(kwargs)
            
            result = await self.db.jobs.update_one(
                {"job_id": job_id},
                {"$set": update_dict}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update job: {e}")
            return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete job and associated proofs"""
        try:
            # Delete job
            job_result = await self.db.jobs.delete_one({"job_id": job_id})
            
            # Delete associated proofs
            await self.db.proofs.delete_one({"job_id": job_id})
            
            return job_result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete job: {e}")
            return False
    
    async def create_proof(self, proof: ProofData) -> ProofData:
        """Store proof data"""
        try:
            proof_dict = proof.model_dump()
            await self.db.proofs.insert_one(proof_dict)
            return proof
            
        except Exception as e:
            logger.error(f"Failed to create proof: {e}")
            raise
    
    async def get_proof(self, job_id: str) -> Optional[ProofData]:
        """Get proof data by job_id"""
        try:
            proof_dict = await self.db.proofs.find_one({"job_id": job_id})
            if proof_dict:
                return ProofData(**proof_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to get proof: {e}")
            return None
    
    async def record_metrics(self, metrics: MetricsData):
        """Record metrics data"""
        try:
            metrics_dict = metrics.model_dump()
            await self.db.metrics.insert_one(metrics_dict)
        except Exception as e:
            logger.error(f"Failed to record metrics: {e}")
    
    async def get_aggregate_metrics(self, days: int = 7) -> dict:
        """Get aggregated metrics for last N days"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {"$match": {"date": {"$gte": start_date}}},
                {
                    "$group": {
                        "_id": None,
                        "total_verifications": {"$sum": "$total_verifications"},
                        "authentic_camera": {"$sum": "$authentic_camera_count"},
                        "authentic_c2pa": {"$sum": "$authentic_c2pa_count"},
                        "ai_generated": {"$sum": "$ai_generated_count"},
                        "unknown": {"$sum": "$unknown_count"},
                        "avg_processing_time": {"$avg": "$average_processing_time_ms"}
                    }
                }
            ]
            
            result = await self.db.metrics.aggregate(pipeline).to_list(1)
            
            if result:
                return result[0]
            
            return {
                "total_verifications": 0,
                "authentic_camera": 0,
                "authentic_c2pa": 0,
                "ai_generated": 0,
                "unknown": 0,
                "avg_processing_time": 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to get aggregate metrics: {e}")
            return {}


# Global database instance
db = Database()
