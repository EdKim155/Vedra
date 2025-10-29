"""
Celery application configuration for Cars Bot.

Provides:
- Redis broker and backend configuration
- Task routing to specialized queues
- Retry policies
- Celery Beat for scheduled tasks
- Monitoring and error handling
"""

import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

# Get configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

# Create Celery app
app = Celery("cars_bot")

# =============================================================================
# BROKER CONFIGURATION (Redis)
# =============================================================================

app.conf.broker_url = CELERY_BROKER_URL
app.conf.result_backend = CELERY_RESULT_BACKEND

# Redis broker settings
app.conf.broker_transport_options = {
    "visibility_timeout": 43200,  # 12 hours - for long-running tasks
    "max_retries": 5,  # Connection retry attempts
    "queue_order_strategy": "priority",  # Enable priority queues
}

# Redis result backend settings
app.conf.result_backend_transport_options = {
    "visibility_timeout": 43200,
    "retry_policy": {
        "timeout": 5.0,  # Connection timeout
        "max_retries": 3,
    },
}

# =============================================================================
# TASK ROUTING & QUEUES
# =============================================================================

# Define exchanges
default_exchange = Exchange("default", type="direct")
ai_exchange = Exchange("ai", type="direct")
publishing_exchange = Exchange("publishing", type="direct")
sheets_exchange = Exchange("sheets", type="direct")
monitoring_exchange = Exchange("monitoring", type="direct")

# Define queues with routing keys
app.conf.task_queues = (
    # Default queue for general tasks
    Queue(
        "default",
        exchange=default_exchange,
        routing_key="default",
        queue_arguments={"x-max-priority": 5},  # Enable priorities 0-5
    ),
    # AI processing queue (CPU/GPU intensive)
    Queue(
        "ai_processing",
        exchange=ai_exchange,
        routing_key="ai.process",
        queue_arguments={
            "x-max-priority": 10,  # Higher priority for AI tasks
            "x-message-ttl": 3600000,  # 1 hour TTL
        },
    ),
    # Publishing queue (Telegram API rate limits)
    Queue(
        "publishing",
        exchange=publishing_exchange,
        routing_key="publishing.post",
        queue_arguments={
            "x-max-priority": 5,
        },
    ),
    # Google Sheets sync queue (API rate limits)
    Queue(
        "sheets_sync",
        exchange=sheets_exchange,
        routing_key="sheets.sync",
        queue_arguments={
            "x-max-priority": 3,
        },
    ),
    # Monitoring & analytics queue
    Queue(
        "monitoring",
        exchange=monitoring_exchange,
        routing_key="monitoring.task",
        queue_arguments={
            "x-max-priority": 3,
        },
    ),
)

# Default queue settings
app.conf.task_default_queue = "default"
app.conf.task_default_exchange = "default"
app.conf.task_default_exchange_type = "direct"
app.conf.task_default_routing_key = "default"

# Task routing rules
app.conf.task_routes = {
    # AI tasks
    "cars_bot.tasks.ai_tasks.process_post_task": {
        "queue": "ai_processing",
        "routing_key": "ai.process",
        "priority": 7,
    },
    "cars_bot.tasks.ai_tasks.classify_post_task": {
        "queue": "ai_processing",
        "routing_key": "ai.process",
        "priority": 8,
    },
    "cars_bot.tasks.ai_tasks.extract_data_task": {
        "queue": "ai_processing",
        "routing_key": "ai.process",
        "priority": 7,
    },
    "cars_bot.tasks.ai_tasks.generate_description_task": {
        "queue": "ai_processing",
        "routing_key": "ai.process",
        "priority": 6,
    },
    # Publishing tasks
    "cars_bot.tasks.publishing_tasks.publish_post_task": {
        "queue": "publishing",
        "routing_key": "publishing.post",
        "priority": 5,
    },
    "cars_bot.tasks.publishing_tasks.send_contact_info_task": {
        "queue": "publishing",
        "routing_key": "publishing.post",
        "priority": 7,  # Higher priority for user interactions
    },
    # Sheets sync tasks
    "cars_bot.tasks.sheets_tasks.sync_channels_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 3,
    },
    "cars_bot.tasks.sheets_tasks.sync_subscribers_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 2,
    },
    "cars_bot.tasks.sheets_tasks.update_analytics_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 1,
    },
    "cars_bot.tasks.sheets_tasks.log_to_sheets_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 2,
    },
    "cars_bot.tasks.sheets_tasks.update_channels_stats_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 2,
    },
    "cars_bot.tasks.sheets_tasks.sync_subscriptions_from_sheets_task": {
        "queue": "sheets_sync",
        "routing_key": "sheets.sync",
        "priority": 3,  # Higher priority - affects user access
    },
    # Monitoring tasks
    "cars_bot.tasks.monitoring_tasks.check_subscriptions_task": {
        "queue": "monitoring",
        "routing_key": "monitoring.task",
        "priority": 2,
    },
    "cars_bot.tasks.monitoring_tasks.collect_stats_task": {
        "queue": "monitoring",
        "routing_key": "monitoring.task",
        "priority": 1,
    },
}

# =============================================================================
# TASK EXECUTION SETTINGS
# =============================================================================

# Task execution
app.conf.task_acks_late = True  # Acknowledge after task completion
app.conf.task_reject_on_worker_lost = True  # Reject tasks if worker dies
app.conf.task_track_started = True  # Track when tasks start
app.conf.task_time_limit = 1800  # Hard time limit: 30 minutes
app.conf.task_soft_time_limit = 1500  # Soft time limit: 25 minutes

# Worker settings
app.conf.worker_prefetch_multiplier = 2  # Tasks to prefetch per worker
app.conf.worker_max_tasks_per_child = 100  # Restart worker after N tasks
app.conf.worker_disable_rate_limits = False  # Enable rate limiting

# =============================================================================
# RETRY POLICIES
# =============================================================================

# Default retry policy for task publishing
app.conf.task_publish_retry = True
app.conf.task_publish_retry_policy = {
    "max_retries": 5,
    "interval_start": 1,  # Start with 1 second
    "interval_step": 2,  # Increase by 2 seconds each retry
    "interval_max": 30,  # Max 30 seconds between retries
}

# Default task retry settings
app.conf.task_autoretry_for = (
    Exception,
)  # Auto-retry on any exception (tasks can override)
app.conf.task_max_retries = 3
app.conf.task_default_retry_delay = 60  # 1 minute default delay

# =============================================================================
# RESULT BACKEND SETTINGS
# =============================================================================

app.conf.result_expires = 86400  # Results expire after 24 hours
app.conf.result_persistent = True  # Persist results to disk
app.conf.result_compression = "gzip"  # Compress results
app.conf.result_extended = True  # Store additional metadata

# =============================================================================
# SERIALIZATION
# =============================================================================

app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]  # Only accept JSON
app.conf.timezone = "UTC"
app.conf.enable_utc = True

# =============================================================================
# CELERY BEAT SCHEDULE (Periodic Tasks)
# =============================================================================

app.conf.beat_schedule = {
    # Sync channels from Google Sheets every minute
    "sync-channels-every-minute": {
        "task": "cars_bot.tasks.sheets_tasks.sync_channels_task",
        "schedule": timedelta(seconds=60),
        "options": {
            "queue": "sheets_sync",
            "priority": 3,
        },
    },
    # Sync subscribers TO Google Sheets - DISABLED to prevent overwriting manual changes
    # New users are added via add_new_user_to_sheets_task automatically
    # Manual subscription changes are synced FROM Google Sheets via sync_subscriptions_from_sheets_task
    # If you need to update user info (username, name, contact count), use update_subscriber_safe_fields()
    # "sync-subscribers-to-sheets-every-5-min": {
    #     "task": "cars_bot.tasks.sheets_tasks.sync_subscribers_task",
    #     "schedule": timedelta(minutes=5),
    #     "options": {
    #         "queue": "sheets_sync",
    #         "priority": 2,
    #     },
    # },
    # Sync subscriptions FROM Google Sheets every 2 minutes (faster for manual management)
    "sync-subscriptions-from-sheets-every-2-min": {
        "task": "cars_bot.tasks.sheets_tasks.sync_subscriptions_from_sheets_task",
        "schedule": timedelta(minutes=2),
        "options": {
            "queue": "sheets_sync",
            "priority": 3,
        },
    },
    # Update analytics every hour
    "update-analytics-hourly": {
        "task": "cars_bot.tasks.sheets_tasks.update_analytics_task",
        "schedule": crontab(minute=0),  # Every hour at :00
        "options": {
            "queue": "sheets_sync",
            "priority": 1,
        },
    },
    # Update channels statistics every hour (at :05 to avoid collision with analytics)
    "update-channels-stats-hourly": {
        "task": "cars_bot.tasks.sheets_tasks.update_channels_stats_task",
        "schedule": crontab(minute=5),  # Every hour at :05
        "options": {
            "queue": "sheets_sync",
            "priority": 2,
        },
    },
    # Check expired subscriptions daily at 00:00
    "check-subscriptions-daily": {
        "task": "cars_bot.tasks.monitoring_tasks.check_subscriptions_task",
        "schedule": crontab(hour=0, minute=0),  # Every day at midnight
        "options": {
            "queue": "monitoring",
            "priority": 2,
        },
    },
    # Collect statistics every 15 minutes
    "collect-stats-every-15-min": {
        "task": "cars_bot.tasks.monitoring_tasks.collect_stats_task",
        "schedule": timedelta(minutes=15),
        "options": {
            "queue": "monitoring",
            "priority": 1,
        },
    },
    # Clean up old task results daily at 03:00
    "cleanup-old-results-daily": {
        "task": "cars_bot.tasks.monitoring_tasks.cleanup_old_results_task",
        "schedule": crontab(hour=3, minute=0),  # Every day at 3 AM
        "options": {
            "queue": "monitoring",
            "priority": 1,
        },
    },
}

# Beat scheduler settings
app.conf.beat_schedule_filename = "celerybeat-schedule"
app.conf.beat_sync_every = 1  # Sync schedule to disk every second

# =============================================================================
# MONITORING & LOGGING
# =============================================================================

# Event settings (for monitoring)
app.conf.worker_send_task_events = True
app.conf.task_send_sent_event = True

# =============================================================================
# TASK DISCOVERY
# =============================================================================

# Auto-discover tasks from these modules
app.autodiscover_tasks(
    [
        "cars_bot.tasks.ai_tasks",
        "cars_bot.tasks.publishing_tasks",
        "cars_bot.tasks.sheets_tasks",
        "cars_bot.tasks.monitoring_tasks",
    ]
)


# =============================================================================
# SIGNALS & HOOKS
# =============================================================================

from celery.signals import (
    task_failure,
    task_retry,
    task_success,
    worker_ready,
    worker_shutdown,
    worker_process_init,
)


@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Called when each worker process starts (for prefork pool)."""
    from cars_bot.config import get_settings
    from cars_bot.database.session import init_database
    
    settings = get_settings()
    init_database(database_url=str(settings.database.url), echo=False)
    
    print(f"🔧 Worker process initialized with database")


@worker_ready.connect
def on_worker_ready(sender, **kwargs):
    """Called when worker is ready."""
    print(f"✅ Celery worker ready: {sender}")


@worker_shutdown.connect
def on_worker_shutdown(sender, **kwargs):
    """Called when worker is shutting down."""
    print(f"🛑 Celery worker shutting down: {sender}")


@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    """Called when task completes successfully."""
    # Log to monitoring system
    pass


@task_failure.connect
def on_task_failure(
    sender=None, task_id=None, exception=None, traceback=None, **kwargs
):
    """Called when task fails."""
    # Log error to Google Sheets and monitoring system
    print(f"❌ Task failed: {sender} - {exception}")


@task_retry.connect
def on_task_retry(sender=None, reason=None, **kwargs):
    """Called when task is retried."""
    print(f"🔄 Task retry: {sender} - {reason}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def get_celery_app() -> Celery:
    """
    Get configured Celery application.

    Returns:
        Configured Celery app instance
    """
    return app


def inspect_celery():
    """
    Inspect Celery workers and queues.

    Returns:
        Dict with inspection results
    """
    inspector = app.control.inspect()

    return {
        "active": inspector.active(),
        "scheduled": inspector.scheduled(),
        "reserved": inspector.reserved(),
        "stats": inspector.stats(),
        "registered": inspector.registered(),
    }


# Alias for backward compatibility
celery_app = app

if __name__ == "__main__":
    # For debugging
    app.start()


