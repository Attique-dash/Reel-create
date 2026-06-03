# SQLite adapter (replaces MongoDB for development)
from .sqlite_adapter import init_db, get_db, JobRepository

__all__ = ['init_db', 'get_db', 'JobRepository']

database = None

async def get_collection(name: str):
    """Get a collection (for MongoDB compatibility)"""
    return JobRepository
