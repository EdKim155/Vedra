"""
Celery tasks for Cars Bot.

All async tasks are organized by domain:
- ai_tasks: AI processing tasks
- publishing_tasks: Publishing to Telegram tasks
- sheets_tasks: Google Sheets synchronization tasks
- monitoring_tasks: Monitoring and maintenance tasks
- subscription_tasks: Subscription management tasks
"""

from cars_bot.tasks.ai_tasks import (
    classify_post_task,
    extract_data_task,
    generate_description_task,
    process_post_task,
)
from cars_bot.tasks.monitoring_tasks import (
    check_subscriptions_task,
    cleanup_old_results_task,
    collect_stats_task,
)
from cars_bot.tasks.publishing_tasks import publish_post_task, send_contact_info_task
from cars_bot.tasks.sheets_tasks import (
    add_new_user_to_sheets_task,
    log_to_sheets_task,
    sync_channels_task,
    sync_subscribers_task,
    sync_subscriptions_from_sheets_task,
    update_analytics_task,
    update_user_contact_count_task,
)
from cars_bot.tasks.subscription_tasks import (
    check_expired_subscriptions,
    cleanup_old_subscriptions,
    send_renewal_reminders,
    update_subscription_analytics,
)

__all__ = [
    # AI tasks
    "process_post_task",
    "classify_post_task",
    "extract_data_task",
    "generate_description_task",
    # Publishing tasks
    "publish_post_task",
    "send_contact_info_task",
    # Sheets tasks
    "sync_channels_task",
    "sync_subscribers_task",
    "sync_subscriptions_from_sheets_task",
    "add_new_user_to_sheets_task",
    "update_user_contact_count_task",
    "update_analytics_task",
    "log_to_sheets_task",
    # Monitoring tasks
    "check_subscriptions_task",
    "collect_stats_task",
    "cleanup_old_results_task",
    # Subscription tasks
    "check_expired_subscriptions",
    "send_renewal_reminders",
    "update_subscription_analytics",
    "cleanup_old_subscriptions",
]


