import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

database = None
client = None

async def init_db():
    """Initialize MongoDB connection"""
    global client, database
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    
    try:
        logger.info(f"🔌 Connecting to MongoDB: {mongodb_uri.split('@')[-1] if '@' in mongodb_uri else mongodb_uri}")
        
        client = AsyncIOMotorClient(
            mongodb_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            socketTimeoutMS=5000,
        )
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ MongoDB connection successful!")
        
        # Get database name from URI or use default
        db_name = "video_processor"
        if "/" in mongodb_uri:
            parts = mongodb_uri.split("/")
            if len(parts) > 3:
                db_name = parts[-1].split("?")[0] or "video_processor"
        
        database = client[db_name]
        logger.info(f"📦 Using database: {db_name}")
        
        # Create indexes
        await database.jobs.create_index([("status", 1)])
        await database.jobs.create_index([("created_at", -1)])
        logger.info("📑 Database indexes created")
        
        print(f"✅ MongoDB connected successfully to {db_name}")
    except Exception as e:
        error_msg = f"MongoDB connection failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        print(f"❌ {error_msg}")
        
        # Provide helpful hints
        if "localhost:27017" in str(e):
            print("\n💡 Hint: Make sure MongoDB is running locally:")
            print("   mongod")
        elif "Connection refused" in str(e):
            print("\n💡 Hint: MongoDB Atlas connection failed. Check:")
            print("   1. Internet connection is active")
            print("   2. MONGODB_URI in .env is correct")
            print("   3. IP whitelist in MongoDB Atlas includes your IP")
            print("   4. Password doesn't contain special characters that need escaping")
        elif "authentication failed" in str(e):
            print("\n💡 Hint: Authentication error with MongoDB Atlas:")
            print("   1. Check username and password in MONGODB_URI")
            print("   2. Make sure credentials are URL-encoded if they contain special chars")
        
        raise

async def get_db():
    """Get database instance"""
    if database is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return database

async def get_collection(name: str):
    """Get a collection"""
    if database is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return database[name]

class JobRepository:
    @staticmethod
    async def create_job(job_id: str, settings: Dict = None, source_type: str = None, source_path: str = None):
        await database.jobs.insert_one({
            "job_id": job_id,
            "status": "pending",
            "progress": 0,
            "video_path": None,
            "clips": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "error": None,
            "settings": settings or {},
            "source_type": source_type,
            "source_path": source_path
        })
    
    @staticmethod
    async def update_job(job_id: str, **kwargs):
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if updates:
            updates["updated_at"] = datetime.utcnow()
            await database.jobs.update_one(
                {"job_id": job_id},
                {"$set": updates}
            )
    
    @staticmethod
    async def get_job(job_id: str) -> Optional[Dict]:
        job = await database.jobs.find_one({"job_id": job_id})
        if job:
            job.pop("_id", None)
            return job
        return None
    
    @staticmethod
    async def list_jobs(limit: int = 10, status: str = None) -> List[Dict]:
        query = {}
        if status:
            query["status"] = status
        
        cursor = database.jobs.find(query).sort("created_at", -1).limit(limit)
        jobs = []
        async for job in cursor:
            job.pop("_id", None)
            jobs.append(job)
        return jobs

__all__ = ['init_db', 'get_db', 'JobRepository', 'get_collection']
