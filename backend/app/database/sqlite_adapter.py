import aiosqlite
import json
import uuid
from typing import Optional, List, Dict, Any

DATABASE_PATH = "./storage/video_processor.db"

async def init_db():
    """Initialize SQLite database"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                progress INTEGER DEFAULT 0,
                video_path TEXT,
                clips TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error TEXT,
                settings TEXT DEFAULT '{}',
                source_type TEXT,
                source_path TEXT
            )
        ''')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_status ON jobs(status)')
        await db.execute('CREATE INDEX IF NOT EXISTS idx_created ON jobs(created_at DESC)')
        await db.commit()
    print("✅ SQLite database initialized")

async def get_db():
    return aiosqlite.connect(DATABASE_PATH)

class JobRepository:
    @staticmethod
    async def create_job(job_id: str, settings: Dict = None, source_type: str = None, source_path: str = None):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "INSERT INTO jobs (job_id, settings, source_type, source_path) VALUES (?, ?, ?, ?)",
                (job_id, json.dumps(settings or {}), source_type, source_path)
            )
            await db.commit()
    
    @staticmethod
    async def update_job(job_id: str, **kwargs):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            updates = []
            values = []
            for key, value in kwargs.items():
                if key == 'clips' and isinstance(value, list):
                    value = json.dumps(value)
                elif key == 'settings' and isinstance(value, dict):
                    value = json.dumps(value)
                updates.append(f"{key} = ?")
                values.append(value)
            updates.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?"
            values.append(job_id)
            await db.execute(query, values)
            await db.commit()
    
    @staticmethod
    async def get_job(job_id: str) -> Optional[Dict]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            async with db.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    job = dict(zip(columns, row))
                    if job.get('clips'):
                        job['clips'] = json.loads(job['clips'])
                    if job.get('settings'):
                        job['settings'] = json.loads(job['settings'])
                    return job
        return None
    
    @staticmethod
    async def list_jobs(limit: int = 10, status: str = None) -> List[Dict]:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            query = "SELECT * FROM jobs"
            params = []
            if status:
                query += " WHERE status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                jobs = []
                for row in rows:
                    job = dict(zip(columns, row))
                    if job.get('clips'):
                        job['clips'] = json.loads(job['clips'])
                    if job.get('settings'):
                        job['settings'] = json.loads(job['settings'])
                    jobs.append(job)
                return jobs
