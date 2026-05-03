"""
Scheduler Module - Handles daily automation tasks
"""
import os
import time
import schedule
import threading
from datetime import datetime
from typing import Callable, Optional
from config import DAILY_UPLOAD_TIME


class AutomationScheduler:
    """Schedules and manages daily automation tasks"""
    
    def __init__(self):
        self.jobs = []
        self.running = False
        self.scheduler_thread = None
    
    def add_daily_job(self, job_func: Callable, time_str: str = DAILY_UPLOAD_TIME,
                     *args, **kwargs):
        """
        Add a daily scheduled job
        
        Args:
            job_func: Function to call
            time_str: Time in "HH:MM" format
        """
        job = schedule.every().day.at(time_str).do(job_func, *args, **kwargs)
        self.jobs.append(job)
        print(f"Scheduled daily job at {time_str}: {job_func.__name__}")
        return job
    
    def add_interval_job(self, job_func: Callable, hours: int = 24,
                        minutes: int = 0, *args, **kwargs):
        """Add an interval-based job"""
        job = schedule.every(hours).hours.do(job_func, *args, **kwargs)
        if minutes > 0:
            job = schedule.every(minutes).minutes.do(job_func, *args, **kwargs)
        self.jobs.append(job)
        print(f"Scheduled interval job (every {hours}h {minutes}m): {job_func.__name__}")
        return job
    
    def run_continuously(self, interval: int = 60):
        """Run the scheduler in a loop"""
        self.running = True
        print(f"Scheduler started. Checking every {interval} seconds.")
        print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        while self.running:
            schedule.run_pending()
            time.sleep(interval)
    
    def start_background(self, interval: int = 60):
        """Start scheduler in a background thread"""
        self.scheduler_thread = threading.Thread(
            target=self.run_continuously,
            args=(interval,),
            daemon=True
        )
        self.scheduler_thread.start()
        print("Scheduler running in background thread")
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        print("Scheduler stopped")
    
    def clear_jobs(self):
        """Clear all scheduled jobs"""
        schedule.clear()
        self.jobs = []
        print("All jobs cleared")
    
    def list_jobs(self):
        """List all scheduled jobs"""
        print("\nScheduled Jobs:")
        print("-" * 40)
        for job in schedule.jobs:
            print(f"  {job}")
        print("-" * 40)


class TaskLogger:
    """Logs automation tasks and their results"""
    
    LOG_FILE = "automation_log.txt"
    
    @staticmethod
    def log(message: str, level: str = "INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        print(log_entry.strip())
        
        with open(TaskLogger.LOG_FILE, 'a') as f:
            f.write(log_entry)
    
    @staticmethod
    def log_task_start(task_name: str):
        """Log task start"""
        TaskLogger.log(f"Starting task: {task_name}")
    
    @staticmethod
    def log_task_complete(task_name: str, result: str = "Success"):
        """Log task completion"""
        TaskLogger.log(f"Completed task: {task_name} - {result}")
    
    @staticmethod
    def log_error(task_name: str, error: str):
        """Log error"""
        TaskLogger.log(f"Error in {task_name}: {error}", level="ERROR")
    
    @staticmethod
    def get_logs(lines: int = 50) -> str:
        """Get recent log entries"""
        try:
            if not os.path.exists(TaskLogger.LOG_FILE):
                return "No logs yet"
            
            with open(TaskLogger.LOG_FILE, 'r') as f:
                all_logs = f.readlines()
                return ''.join(all_logs[-lines:])
        except Exception as e:
            return f"Error reading logs: {e}"


# Wrapper decorator for logging
def logged_task(task_name: str):
    """Decorator to automatically log task execution"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            TaskLogger.log_task_start(task_name)
            try:
                result = func(*args, **kwargs)
                TaskLogger.log_task_complete(task_name, "Success")
                return result
            except Exception as e:
                TaskLogger.log_error(task_name, str(e))
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test scheduler
    def test_job():
        print(f"Test job executed at {datetime.now()}")
    
    scheduler = AutomationScheduler()
    scheduler.add_daily_job(test_job, "09:00")
    scheduler.list_jobs()
    
    # Test logging
    TaskLogger.log("Scheduler test started")
    TaskLogger.log_task_start("TestTask")
    TaskLogger.log_task_complete("TestTask")
