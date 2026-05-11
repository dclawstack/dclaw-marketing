"""Celery worker package.

Public surface:
- `celery_app`: the configured Celery instance (run with `celery -A app.worker.celery_app worker`)
- `update_job`: helper for tasks to update their Job row's progress/result/error
"""

from app.worker.celery_app import celery_app
from app.worker.helpers import update_job

__all__ = ["celery_app", "update_job"]
