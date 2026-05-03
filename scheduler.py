"""
Scheduler Module - Handles daily automation tasks
"""
import os
import time
import schedule
import threading
import functools  # FIX: needed for wraps
from datetime import datetime
from typing import Callable, Optional
from config import DAILY_UPLOAD_TIME


class AutomationScheduler:
    """Schedules and manages daily automation tasks"""

    def __init__(self):
        self.jobs = []
        self.running = False
        self.scheduler_thread = None

    def add_daily_job(
        self, job_func: Callable, time_str: str = DAILY_UPLOAD_TIME, *args, **kwargs
    ):
        job = schedule.every().day.at(time_str).do(job_func, *args, **kwargs)
        self.jobs.append(job)
        print(f"[Scheduler] Daily job registered at {time_str}: {job_func.__name__}")
        return job

    def add_interval_job(
        self, job_func: Callable, hours: int = 24, minutes: int = 0, *args, **kwargs
    ):
        if minutes > 0:
            job = schedule.every(minutes).minutes.do(job_func, *args, **kwargs)
        else:
            job = schedule.every(hours).hours.do(job_func, *args, **kwargs)
        self.jobs.append(job)
        print(f"[Scheduler] Interval job registered (every {hours}h {minutes}m): {job_func.__name__}")
        return job

    def run_continuously(self, interval: int = 60):
        self.running = True
        print(f"[Scheduler] Started. Checking every {interval}s.")
        print(f"[Scheduler] Current time: {datetime.now():%Y-%m-%d %H:%M:%S}")
        while self.running:
            schedule.run_pending()
            time.sleep(interval)

    def start_background(self, interval: int = 60):
        self.scheduler_thread = threading.Thread(
            target=self.run_continuously,
            args=(interval,),
            daemon=True,
        )
        self.scheduler_thread.start()
        print("[Scheduler] Running in background thread.")

    def stop(self):
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)
        print("[Scheduler] Stopped.")

    def clear_jobs(self):
        schedule.clear()
        self.jobs = []
        print("[Scheduler] All jobs cleared.")

    def list_jobs(self):
        print("\nScheduled jobs:")
        print("-" * 40)
        for job in schedule.jobs:
            print(f"  {job}")
        print("-" * 40)


class TaskLogger:
    """Logs automation tasks and their results"""

    LOG_FILE = "automation_log.txt"

    @staticmethod
    def log(message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"
        print(entry.strip())
        with open(TaskLogger.LOG_FILE, "a") as f:
            f.write(entry)

    @staticmethod
    def log_task_start(task_name: str):
        TaskLogger.log(f"Starting: {task_name}")

    @staticmethod
    def log_task_complete(task_name: str, result: str = "Success"):
        TaskLogger.log(f"Completed: {task_name} — {result}")

    @staticmethod
    def log_error(task_name: str, error: str):
        TaskLogger.log(f"Error in {task_name}: {error}", level="ERROR")

    @staticmethod
    def get_logs(lines: int = 50) -> str:
        try:
            if not os.path.exists(TaskLogger.LOG_FILE):
                return "No logs yet."
            with open(TaskLogger.LOG_FILE, "r") as f:
                return "".join(f.readlines()[-lines:])
        except Exception as e:
            return f"Error reading logs: {e}"


def logged_task(task_name: str):
    """
    Decorator to automatically log task execution.
    FIX: use @functools.wraps(func) so the original __name__ is preserved.
    """
    def decorator(func):
        @functools.wraps(func)  # FIX
        def wrapper(*args, **kwargs):
            TaskLogger.log_task_start(task_name)
            try:
                result = func(*args, **kwargs)
                TaskLogger.log_task_complete(task_name)
                return result
            except Exception as e:
                TaskLogger.log_error(task_name, str(e))
                raise
        return wrapper
    return decorator


if __name__ == "__main__":
    def test_job():
        print(f"Test job executed at {datetime.now()}")

    scheduler = AutomationScheduler()
    scheduler.add_daily_job(test_job, "09:00")
    scheduler.list_jobs()

    TaskLogger.log("Scheduler test started")
    TaskLogger.log_task_start("TestTask")
    TaskLogger.log_task_complete("TestTask")