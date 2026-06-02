from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    database_name: str = "video_processor"

settings = Settings()

client: AsyncIOMotorClient = None
database = None

async def init_db():
    global client, database
    client = AsyncIOMotorClient(settings.mongodb_uri)
    database = client[settings.database_name]
    
    # Create indexes
    await database.jobs.create_index("job_id", unique=True)
    await database.jobs.create_index("status")
    await database.jobs.create_index("created_at")
    
    print(f"Connected to MongoDB: {settings.database_name}")

async def get_db():
    return database
