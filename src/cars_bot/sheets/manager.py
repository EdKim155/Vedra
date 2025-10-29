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
    SubscriptionTypeEnum,
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
                    # Get username and validate it's not empty
                    username = str(record.get("Username канала", "")).strip()
                    if not username or username == '@':
                        logger.warning(
                            f"Skipping channel row with empty username: {record}"
                        )
                        continue
                    
                    # Convert TRUE/FALSE strings to boolean
                    if isinstance(record.get("Активен"), str):
                        record["Активен"] = record["Активен"].upper() == "TRUE"
                    
                    # Parse date_added if present
                    date_added = None
                    date_added_str = record.get("Дата добавления", "")
                    if date_added_str and date_added_str.strip():
                        try:
                            date_added = datetime.strptime(date_added_str, "%Y-%m-%d %H:%M:%S")
                        except (ValueError, TypeError):
                            logger.debug(f"Could not parse date_added: {date_added_str}")

                    channel = ChannelRow(
                        id=record.get("ID"),
                        username=username,
                        title=record.get("Название канала", ""),
                        is_active=record.get("Активен", True),
                        date_added=date_added,
                        published_posts=int(record.get("Опубликовано", 0) or 0),
                        last_post_link=record.get("Последний пост"),
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

    def get_subscribers(self, use_cache: bool = True) -> list[SubscriberRow]:
        """
        Get list of subscribers from Google Sheets.

        Args:
            use_cache: Whether to use cached data

        Returns:
            List of subscriber data
        """
        cache_key = "subscribers"

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        try:
            worksheet = self._get_worksheet(self.SHEET_SUBSCRIBERS)
            self.rate_limiter.wait_if_needed()

            # Get all records (skip header row)
            records = worksheet.get_all_records()

            subscribers = []
            for record in records:
                try:
                    # Get user_id and validate it's not empty
                    user_id = record.get("User ID", "")
                    if not user_id or str(user_id).strip() == "":
                        logger.warning(
                            f"Skipping subscriber row with empty user_id: {record}"
                        )
                        continue

                    # Convert TRUE/FALSE strings to boolean
                    if isinstance(record.get("Активна"), str):
                        record["Активна"] = record["Активна"].upper() == "TRUE"

                    # Parse subscription type
                    sub_type_str = str(record.get("Тип подписки", "FREE")).upper()
                    try:
                        subscription_type = SubscriptionTypeEnum(sub_type_str)
                    except ValueError:
                        logger.warning(
                            f"Invalid subscription type '{sub_type_str}' for user {user_id}, "
                            f"defaulting to FREE"
                        )
                        subscription_type = SubscriptionTypeEnum.FREE

                    # Parse dates
                    start_date = None
                    start_date_str = record.get("Дата начала", "")
                    if start_date_str and str(start_date_str).strip():
                        try:
                            start_date = datetime.strptime(
                                str(start_date_str), "%Y-%m-%d %H:%M:%S"
                            )
                        except (ValueError, TypeError):
                            logger.debug(f"Could not parse start_date: {start_date_str}")

                    end_date = None
                    end_date_str = record.get("Дата окончания", "")
                    if end_date_str and str(end_date_str).strip():
                        try:
                            end_date = datetime.strptime(
                                str(end_date_str), "%Y-%m-%d %H:%M:%S"
                            )
                        except (ValueError, TypeError):
                            logger.debug(f"Could not parse end_date: {end_date_str}")

                    registration_date = None
                    registration_date_str = record.get("Дата регистрации", "")
                    if registration_date_str and str(registration_date_str).strip():
                        try:
                            registration_date = datetime.strptime(
                                str(registration_date_str), "%Y-%m-%d %H:%M:%S"
                            )
                        except (ValueError, TypeError):
                            logger.debug(
                                f"Could not parse registration_date: {registration_date_str}"
                            )

                    # If no registration date, use current time
                    if not registration_date:
                        registration_date = datetime.utcnow()

                    subscriber = SubscriberRow(
                        user_id=int(user_id),
                        username=record.get("Username", ""),
                        name=record.get("Имя", ""),
                        subscription_type=subscription_type,
                        is_active=record.get("Активна", True),
                        start_date=start_date,
                        end_date=end_date,
                        registration_date=registration_date,
                        contact_requests=int(record.get("Запросов контактов", 0) or 0),
                    )
                    subscribers.append(subscriber)
                except Exception as e:
                    logger.error(f"Error parsing subscriber row: {record}. Error: {e}")
                    continue

            logger.info(f"Loaded {len(subscribers)} subscribers from Google Sheets")

            # Cache the results (shorter TTL for subscribers as they change more often)
            self._set_cache(cache_key, subscribers, ttl=30)

            return subscribers

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error reading subscribers: {e}")
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
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> None:
        """
        Update subscriber status.

        Args:
            user_id: Telegram user ID
            subscription_type: New subscription type
            is_active: New active status
            start_date: New start date
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
            if start_date is not None:
                updates.append(
                    gspread.Cell(row, 6, start_date.strftime("%Y-%m-%d %H:%M:%S"))
                )  # Column F
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

    def update_subscribers(self, subscribers_data: list[dict]) -> None:
        """
        Bulk update all subscribers in the sheet.
        
        ⚠️ DEPRECATED: This method overwrites manual subscription changes!
        Use update_subscriber_safe_fields() instead for existing users.

        Args:
            subscribers_data: List of subscriber dictionaries with keys:
                - user_id
                - username
                - first_name
                - last_name
                - subscription_type
                - is_active
                - start_date
                - end_date
                - registered_at
        """
        logger.warning(
            "update_subscribers() is deprecated and overwrites manual changes. "
            "Consider using update_subscriber_safe_fields() instead."
        )
        
        try:
            worksheet = self._get_worksheet(self.SHEET_SUBSCRIBERS)
            
            # Clear existing data (except header) by deleting rows 2 onwards
            self.rate_limiter.wait_if_needed()
            all_values = worksheet.get_all_values()
            
            # If there are rows beyond header, delete them
            if len(all_values) > 1:
                # Delete all rows except header (row 1)
                worksheet.delete_rows(2, len(all_values))
                self.rate_limiter.wait_if_needed()
            
            if not subscribers_data:
                logger.info("No subscribers to update")
                return
            
            # Prepare rows
            rows = []
            for sub in subscribers_data:
                row = [
                    sub.get("user_id", ""),
                    sub.get("username", ""),
                    f"{sub.get('first_name', '')} {sub.get('last_name', '')}".strip(),
                    sub.get("subscription_type", "FREE"),
                    "TRUE" if sub.get("is_active", False) else "FALSE",
                    sub.get("start_date").strftime("%Y-%m-%d %H:%M:%S") if sub.get("start_date") else "",
                    sub.get("end_date").strftime("%Y-%m-%d %H:%M:%S") if sub.get("end_date") else "",
                    sub.get("registered_at").strftime("%Y-%m-%d %H:%M:%S") if sub.get("registered_at") else "",
                    0,  # contact_requests - placeholder
                ]
                rows.append(row)
            
            # Batch update
            self.rate_limiter.wait_if_needed()
            worksheet.append_rows(rows, value_input_option="USER_ENTERED")
            
            logger.info(f"Updated {len(subscribers_data)} subscribers in Google Sheets")

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error bulk updating subscribers: {e}")
            raise
    
    def update_subscriber_safe_fields(
        self,
        user_id: int,
        username: Optional[str] = None,
        name: Optional[str] = None,
        contact_requests: Optional[int] = None,
    ) -> bool:
        """
        Update only safe fields (non-subscription) for existing subscriber.
        
        This method DOES NOT touch subscription columns (Type, Active, Start Date, End Date).
        Use this to update user info without overwriting manual subscription changes.
        
        Args:
            user_id: Telegram user ID
            username: Username to update (Column B)
            name: Full name to update (Column C)
            contact_requests: Contact requests count (Column I)
        
        Returns:
            True if updated, False if user not found
        """
        try:
            worksheet = self._get_worksheet(self.SHEET_SUBSCRIBERS)
            self.rate_limiter.wait_if_needed()
            
            # Find the row with this user
            cell = worksheet.find(str(user_id))
            
            if cell is None:
                logger.debug(f"Subscriber {user_id} not found in sheet for safe update")
                return False
            
            row = cell.row
            
            # Update only safe fields (NOT subscription columns D, E, F, G)
            updates = []
            if username is not None:
                updates.append(gspread.Cell(row, 2, username))  # Column B
            if name is not None:
                updates.append(gspread.Cell(row, 3, name))  # Column C
            if contact_requests is not None:
                updates.append(gspread.Cell(row, 9, contact_requests))  # Column I
            
            if updates:
                self.rate_limiter.wait_if_needed()
                worksheet.update_cells(updates)
                logger.debug(f"Updated safe fields for subscriber {user_id}")
                return True
            
            return False

        except APIError as e:
            logger.error(f"Google Sheets API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error updating subscriber safe fields: {e}")
            return False

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
