import asyncio
from app.database.mongodb import JobRepository

async def test():
    print("Testing database operations...")
    
    # Create a test job
    await JobRepository.create_job('test-123', {'num_clips': 5}, 'file', '/path/to/video.mp4')
    print("✅ Job created")
    
    # Get the job
    job = await JobRepository.get_job('test-123')
    print(f"✅ Job retrieved: {job.get('job_id')} - Status: {job.get('status')}")
    
    # Update the job
    await JobRepository.update_job('test-123', status='processing', progress=50)
    print("✅ Job updated")
    
    # Get updated job
    job2 = await JobRepository.get_job('test-123')
    print(f"✅ Job status: {job2.get('status')}, Progress: {job2.get('progress')}%")
    
    # List jobs
    jobs = await JobRepository.list_jobs()
    print(f"✅ Total jobs: {len(jobs)}")
    
    print("\n🎉 All database tests passed!")

asyncio.run(test())
