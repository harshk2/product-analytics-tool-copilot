"""Celery application instance and configuration."""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "analytics_copilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.investigations",
        "app.tasks.analytics",
    ],
)

# ── Celery Configuration ────────────────────────────────────────────────────────

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task behavior
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,   # 5 minutes soft limit
    task_time_limit=600,        # 10 minutes hard limit

    # Result storage
    result_expires=86400,       # Results stored for 24 hours

    # Retry settings
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute

    # Queue routing
    task_routes={
        "app.tasks.investigations.*": {"queue": "investigations"},
        "app.tasks.analytics.*": {"queue": "default"},
    },

    # Beat schedule (periodic tasks)
    beat_schedule={
        # Refresh materialized views every hour
        "refresh-materialized-views": {
            "task": "app.tasks.analytics.refresh_materialized_views",
            "schedule": crontab(minute=0),  # Top of every hour
        },

        # Compute daily metrics at 1 AM UTC
        "compute-daily-metrics": {
            "task": "app.tasks.analytics.compute_daily_metrics",
            "schedule": crontab(hour=1, minute=0),
        },

        # Clean up old in-progress investigations (stale)
        "cleanup-stale-investigations": {
            "task": "app.tasks.investigations.cleanup_stale_investigations",
            "schedule": crontab(hour=2, minute=0),
        },

        # Run anomaly detection on all key metrics daily at 6 AM
        "daily-anomaly-detection": {
            "task": "app.tasks.analytics.run_anomaly_detection",
            "schedule": crontab(hour=6, minute=0),
        },
    },
)
