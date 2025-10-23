"""
Google Sheets Manager for Cars Bot.

Handles all interactions with Google Sheets for configuration and analytics.
"""

import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound

from cars_bot.sheets.models import (
    AnalyticsRow,
    ChannelRow,
    FilterSettings,
    LogLevel,
    LogRow,
    QueueRow,
    SubscriberRow,
)

logger = logging.getLogger(__name__)


class CacheEntry:
    """Cache entry with expiration."""

    def __init__(self, data: Any, ttl: int):
        """
        Initialize cache entry.

        Args:
            data: Data to cache
            ttl: Time to live in seconds
        """
        self.data = data
        self.expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return datetime.utcnow() > self.expires_at


class RateLimiter:
    """Simple rate limiter for Google Sheets API."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 100):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: list[float] = []

    def wait_if_needed(self) -> None:
        """Wait if rate limit is exceeded."""
        now = time.time()

        # Remove old requests outside the window
        self.requests = [req for req in self.requests if now - req < self.window_seconds]

        if len(self.requests) >= self.max_requests:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = self.window_seconds - (now - oldest_request) + 1
            if wait_time > 0:
                logger.warning(f"Rate limit reached. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                # Clear old requests after waiting
                now = time.time()
                self.requests = [req for req in self.requests if now - req < self.window_seconds]

        # Record this request
        self.requests.append(now)


class GoogleSheetsManager:
    """
    Manager for Google Sheets operations.

    Handles reading configuration and writing statistics/logs to Google Sheets.
    """

    # Sheet names (must match names in Google Sheets)
    SHEET_CHANNELS = "Каналы для мониторинга"
    SHEET_FILTERS = "Настройки фильтров"
    SHEET_SUBSCRIBERS = "Подписчики"
    SHEET_ANALYTICS = "Аналитика"
    SHEET_QUEUE = "Очередь публикаций"
    SHEET_LOGS = "Логи"

    def __init__(
        self,
        credentials_path: str | Path,
        spreadsheet_id: str,
        cache_ttl: int = 60,
        rate_limit_requests: int = 100,
        rate_limit_window: int = 100,
    ):
        """
        Initialize Google Sheets manager.

        Args:
            credentials_path: Path to service account JSON credentials
            spreadsheet_id: Google Sheets spreadsheet ID
            cache_ttl: Cache time-to-live in seconds
            rate_limit_requests: Max requests per window
            rate_limit_window: Rate limit window in seconds
        """
        self.spreadsheet_id = spreadsheet_id
        self.cache_ttl = cache_ttl

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=rate_limit_requests,
            window_seconds=rate_limit_window,
        )

        # Initialize cache
        self._cache: dict[str, CacheEntry] = {}

        # Initialize gspread client
        self.client = self._init_client(credentials_path)
        self.spreadsheet: Optional[gspread.Spreadsheet] = None

    def _init_client(self, credentials_path: str | Path) -> gspread.Client:
        """
        Initialize gspread client with service account credentials.

        Args:
            credentials_path: Path to JSON credentials file

        Returns:
            Authorized gspread client
        """
        credentials_path = Path(credentials_path)

        if not credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {credentials_path}")

        # Define required scopes
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        # Load credentials
        creds = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=scopes,
        )

        # Authorize client
        client = gspread.authorize(creds)
        logger.info("Google Sheets client initialized successfully")

        return client

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """
        Get spreadsheet object (cached).

        Returns:
            Spreadsheet object
        """
        if self.spreadsheet is None:
            try:
                self.rate_limiter.wait_if_needed()
                self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
                logger.info(f"Opened spreadsheet: {self.spreadsheet.title}")
            except SpreadsheetNotFound:
                raise ValueError(
                    f"Spreadsheet not found: {self.spreadsheet_id}. "
                    "Make sure the service account has access."
                )

        return self.spreadsheet

    def _get_worksheet(self, sheet_name: str) -> gspread.Worksheet:
        """
        Get worksheet by name.

        Args:
            sheet_name: Name of the worksheet

        Returns:
            Worksheet object
        """
        spreadsheet = self._get_spreadsheet()

        try:
            self.rate_limiter.wait_if_needed()
            worksheet = spreadsheet.worksheet(sheet_name)
            return worksheet
        except WorksheetNotFound:
            raise ValueError(
                f"Worksheet '{sheet_name}' not found in spreadsheet. "
                f"Available sheets: {[ws.title for ws in spreadsheet.worksheets()]}"
            )

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                logger.debug(f"Cache hit: {key}")
                return entry.data
            else:
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """Set data in cache."""
        if ttl is None:
            ttl = self.cache_ttl
        self._cache[key] = CacheEntry(data, ttl)
        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def clear_cache(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    # =========================================================================
    # READ METHODS
    # =========================================================================

    def get_channels(self, use_cache: bool = True) -> list[ChannelRow]:
        """
        Get list of channels to monitor.

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of channel configurations
        """
        cache_key = "channels"

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        try:
            worksheet = self._get_worksheet(self.SHEET_CHANNELS)
            self.rate_limiter.wait_if_needed()

            # Get all records (skip header row)
            records = worksheet.get_all_records()

            channels = []
            for record in records:
                try:
                    # Convert TRUE/FALSE strings to boolean
                    if isinstance(record.get("Активен"), str):
                        record["Активен"] = record["Активен"].upper() == "TRUE"

                    channel = ChannelRow(
                        id=record.get("ID"),
                        username=record.get("Username канала", ""),
                        title=record.get("Название канала", ""),
                        is_active=record.get("Активен", True),
                        keywords=record.get("Ключевые слова"),
                        total_posts=int(record.get("Всего постов", 0) or 0),
                        published_posts=int(record.get("Опубликовано", 0) or 0),
                    )
                    channels.append(channel)
                except Exception as e:
                    logger.error(f"Error parsing channel row: {record}. Error: {e}")
                    continue

            logger.info(f"Loaded {len(channels)} channels from Google Sheets")

            # Cache the results
            self._set_cache(cache_key, channels)

            return channels

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading channels: {e}")
            raise

    def get_filter_settings(self, use_cache: bool = True) -> FilterSettings:
        """
        Get filter settings.

        Args:
            use_cache: Whether to use cached data

        Returns:
            Filter settings
        """
        cache_key = "filter_settings"

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        try:
            worksheet = self._get_worksheet(self.SHEET_FILTERS)
            self.rate_limiter.wait_if_needed()

            # Get all values (expecting key-value pairs)
            values = worksheet.get_all_values()

            # Parse settings (skip header)
            settings_dict = {}
            for row in values[1:]:  # Skip header row
                if len(row) >= 2 and row[0]:
                    key = row[0].strip()
                    value = row[1].strip() if row[1] else None
                    settings_dict[key] = value

            # Map to FilterSettings model
            settings = FilterSettings(
                global_keywords=settings_dict.get("Глобальные ключевые слова"),
                min_confidence_score=float(
                    settings_dict.get("Порог уверенности AI", 0.75)
                ),
                min_price=int(settings_dict["Минимальная цена"])
                if settings_dict.get("Минимальная цена")
                else None,
                max_price=int(settings_dict["Максимальная цена"])
                if settings_dict.get("Максимальная цена")
                else None,
                excluded_words=settings_dict.get("Исключаемые слова"),
            )

            logger.info("Loaded filter settings from Google Sheets")

            # Cache the results
            self._set_cache(cache_key, settings)

            return settings

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading filter settings: {e}")
            raise

    # =========================================================================
    # WRITE METHODS
    # =========================================================================

    def update_channel_stats(
        self,
        channel_username: str,
        total_posts: Optional[int] = None,
        published_posts: Optional[int] = None,
        last_post_date: Optional[datetime] = None,
    ) -> None:
        """
        Update channel statistics.

        Args:
            channel_username: Channel username to update
            total_posts: New total posts count
            published_posts: New published posts count
            last_post_date: Date of last post
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_CHANNELS)
            self.rate_limiter.wait_if_needed()

            # Find the row with this channel
            cell = worksheet.find(channel_username)

            if cell is None:
                logger.warning(f"Channel {channel_username} not found in sheet")
                return

            row = cell.row

            # Update statistics
            updates = []
            if total_posts is not None:
                updates.append(
                    gspread.Cell(row, 7, total_posts)  # Column G: Всего постов
                )
            if published_posts is not None:
                updates.append(
                    gspread.Cell(row, 8, published_posts)  # Column H: Опубликовано
                )
            if last_post_date is not None:
                updates.append(
                    gspread.Cell(
                        row, 9, last_post_date.strftime("%Y-%m-%d %H:%M:%S")
                    )  # Column I
                )

            if updates:
                self.rate_limiter.wait_if_needed()
                worksheet.update_cells(updates)
                logger.info(f"Updated stats for channel: {channel_username}")

                # Clear channels cache
                if "channels" in self._cache:
                    del self._cache["channels"]

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating channel stats: {e}")
            raise

    def add_subscriber(self, subscriber: SubscriberRow) -> None:
        """
        Add new subscriber to the sheet.

        Args:
            subscriber: Subscriber data
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_SUBSCRIBERS)

            # Prepare row data
            row_data = [
                subscriber.user_id,
                subscriber.username or "",
                subscriber.name,
                subscriber.subscription_type.value,
                "TRUE" if subscriber.is_active else "FALSE",
                subscriber.start_date.strftime("%Y-%m-%d %H:%M:%S")
                if subscriber.start_date
                else "",
                subscriber.end_date.strftime("%Y-%m-%d %H:%M:%S")
                if subscriber.end_date
                else "",
                subscriber.registration_date.strftime("%Y-%m-%d %H:%M:%S"),
                subscriber.contact_requests,
            ]

            self.rate_limiter.wait_if_needed()
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")

            logger.info(f"Added subscriber: {subscriber.user_id}")

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding subscriber: {e}")
            raise

    def update_subscriber_status(
        self,
        user_id: int,
        subscription_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        end_date: Optional[datetime] = None,
    ) -> None:
        """
        Update subscriber status.

        Args:
            user_id: Telegram user ID
            subscription_type: New subscription type
            is_active: New active status
            end_date: New end date
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_SUBSCRIBERS)
            self.rate_limiter.wait_if_needed()

            # Find the row with this user
            cell = worksheet.find(str(user_id))

            if cell is None:
                logger.warning(f"Subscriber {user_id} not found in sheet")
                return

            row = cell.row

            # Update fields
            updates = []
            if subscription_type is not None:
                updates.append(gspread.Cell(row, 4, subscription_type))  # Column D
            if is_active is not None:
                updates.append(
                    gspread.Cell(row, 5, "TRUE" if is_active else "FALSE")  # Column E
                )
            if end_date is not None:
                updates.append(
                    gspread.Cell(row, 7, end_date.strftime("%Y-%m-%d %H:%M:%S"))
                )  # Column G

            if updates:
                self.rate_limiter.wait_if_needed()
                worksheet.update_cells(updates)
                logger.info(f"Updated subscriber: {user_id}")

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error updating subscriber: {e}")
            raise

    def write_log(self, log_entry: LogRow) -> None:
        """
        Write log entry to logs sheet.

        Args:
            log_entry: Log entry to write
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_LOGS)

            # Prepare row data
            row_data = [
                log_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log_entry.level.value,
                log_entry.message,
                log_entry.component,
            ]

            self.rate_limiter.wait_if_needed()
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")

            logger.debug(f"Logged to Google Sheets: {log_entry.level} - {log_entry.message}")

        except APIError as e:
            logger.error(f"Google Sheets API error while writing log: {e}")
            # Don't raise - logging errors shouldn't break the app
        except Exception as e:
            logger.error(f"Error writing log to sheet: {e}")
            # Don't raise - logging errors shouldn't break the app

    def write_analytics(self, analytics: AnalyticsRow) -> None:
        """
        Write analytics row to analytics sheet.

        Args:
            analytics: Analytics data for the day
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_ANALYTICS)

            # Prepare row data
            row_data = [
                analytics.date.strftime("%Y-%m-%d"),
                analytics.posts_processed,
                analytics.posts_published,
                analytics.new_subscribers,
                analytics.active_subscriptions,
                analytics.contact_requests,
                analytics.revenue,
            ]

            self.rate_limiter.wait_if_needed()
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")

            logger.info(f"Wrote analytics for {analytics.date.date()}")

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error writing analytics: {e}")
            raise

    def add_to_queue(self, queue_entry: QueueRow) -> None:
        """
        Add post to publication queue.

        Args:
            queue_entry: Queue entry data
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_QUEUE)

            # Prepare row data
            row_data = [
                queue_entry.post_id,
                queue_entry.source_channel,
                queue_entry.processed_date.strftime("%Y-%m-%d %H:%M:%S"),
                queue_entry.car_info,
                queue_entry.price or "",
                queue_entry.status.value,
                queue_entry.original_link or "",
                queue_entry.notes or "",
            ]

            self.rate_limiter.wait_if_needed()
            worksheet.append_row(row_data, value_input_option="USER_ENTERED")

            logger.info(f"Added post {queue_entry.post_id} to queue")

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
            raise
