"""
Scheduler Module
"""
import os
import time
import schedule
import threading
import functools
from datetime import datetime
from typing import Callable
from config import DAILY_UPLOAD_TIME


class AutomationScheduler:
    def __init__(self):
        self.jobs = []
        self.running = False
        self.scheduler_thread = None

    def add_daily_job(self, job_func: Callable, time_str: str = DAILY_UPLOAD_TIME,
                      *args, **kwargs):
        job = schedule.every().day.at(time_str).do(job_func, *args, **kwargs)
        self.jobs.append(job)
        print(f"[Scheduler] Daily job at {time_str}: {job_func.__name__}")
        return job

    def run_continuously(self, interval: int = 60):
        self.running = True
        while self.running:
            schedule.run_pending()
            time.sleep(interval)

    def start_background(self, interval: int = 60):
        self.scheduler_thread = threading.Thread(
            target=self.run_continuously, args=(interval,), daemon=True)
        self.scheduler_thread.start()

    def stop(self):
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)


class TaskLogger:
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
    def log_task_complete(task_name: str):
        TaskLogger.log(f"Completed: {task_name}")

    @staticmethod
    def log_error(task_name: str, error: str):
        TaskLogger.log(f"Error in {task_name}: {error}", level="ERROR")


def logged_task(task_name: str):
    def decorator(func):
        @functools.wraps(func)
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