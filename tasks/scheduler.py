"""
定时任务调度器
使用 APScheduler 实现定时任务功能
"""
import logging
from typing import Callable, Optional, Dict
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from config.settings import settings

logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    定时任务调度器
    支持：
    - 固定间隔任务
    - Cron 表达式任务
    - 一次性任务
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._tasks = {}
    
    def start(self):
        """启动调度器"""
        if settings.SCHEDULER_ENABLED:
            self.scheduler.start()
            logger.info("Task scheduler started")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("Task scheduler stopped")
    
    def add_interval_task(
        self,
        task_id: str,
        func: Callable,
        seconds: int = None,
        minutes: int = None,
        hours: int = None,
        **kwargs
    ):
        """
        添加间隔执行任务
        
        Args:
            task_id: 任务ID
            func: 执行的函数
            seconds: 秒数
            minutes: 分钟数
            hours: 小时数
            **kwargs: 传递给函数的额外参数
        """
        trigger = IntervalTrigger(
            seconds=seconds,
            minutes=minutes,
            hours=hours
        )
        
        self.scheduler.add_job(
            func,
            trigger,
            id=task_id,
            kwargs=kwargs,
            replace_existing=True
        )
        
        self._tasks[task_id] = {
            "type": "interval",
            "func": func,
            "next_run": self.scheduler.get_job(task_id).next_run_time
        }
        
        logger.info(f"Added interval task: {task_id}")
    
    def add_cron_task(
        self,
        task_id: str,
        func: Callable,
        cron_expr: str = None,
        **kwargs
    ):
        """
        添加 Cron 表达式任务
        
        Args:
            task_id: 任务ID
            func: 执行的函数
            cron_expr: Cron 表达式 (如 "0 9 * * *" 表示每天9点)
            **kwargs: 传递给函数的额外参数
        """
        trigger = CronTrigger.from_crontab(cron_expr)
        
        self.scheduler.add_job(
            func,
            trigger,
            id=task_id,
            kwargs=kwargs,
            replace_existing=True
        )
        
        self._tasks[task_id] = {
            "type": "cron",
            "cron": cron_expr,
            "func": func,
            "next_run": self.scheduler.get_job(task_id).next_run_time
        }
        
        logger.info(f"Added cron task: {task_id}, schedule: {cron_expr}")
    
    def add_once_task(
        self,
        task_id: str,
        func: Callable,
        run_date: datetime,
        **kwargs
    ):
        """
        添加一次性任务
        
        Args:
            task_id: 任务ID
            func: 执行的函数
            run_date: 执行时间
            **kwargs: 传递给函数的额外参数
        """
        self.scheduler.add_job(
            func,
            "date",
            id=task_id,
            run_date=run_date,
            kwargs=kwargs,
            replace_existing=True
        )
        
        self._tasks[task_id] = {
            "type": "once",
            "func": func,
            "scheduled_time": run_date
        }
        
        logger.info(f"Added once task: {task_id}, scheduled for {run_date}")
    
    def remove_task(self, task_id: str):
        """
        移除任务
        
        Args:
            task_id: 任务ID
        """
        self.scheduler.remove_job(task_id)
        self._tasks.pop(task_id, None)
        logger.info(f"Removed task: {task_id}")
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[Dict]: 任务信息
        """
        return self._tasks.get(task_id)
    
    def list_tasks(self) -> Dict[str, Dict]:
        """
        列出所有任务
        
        Returns:
            Dict[str, Dict]: 所有任务的信息
        """
        result = {}
        for task_id, info in self._tasks.items():
            job = self.scheduler.get_job(task_id)
            if job:
                result[task_id] = {
                    **info,
                    "next_run": job.next_run_time,
                    "pending": job.pending
                }
        return result
    
    def pause_task(self, task_id: str):
        """暂停任务"""
        self.scheduler.pause_job(task_id)
        logger.info(f"Paused task: {task_id}")
    
    def resume_task(self, task_id: str):
        """恢复任务"""
        self.scheduler.resume_job(task_id)
        logger.info(f"Resumed task: {task_id}")
