"""
Unit tests for MessageProcessor.

Tests cover:
- Pydantic model validation
- Contact extraction from various formats
- Keyword filtering
- Duplicate detection
- Database integration
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError

from cars_bot.monitor.message_processor import (
    ContactInfo,
    MediaInfo,
    MessageData,
    MessageProcessor,
)


class TestContactInfo:
    """Test ContactInfo Pydantic model."""
    
    def test_valid_contact_with_username(self):
        """Test creating contact with username."""
        contact = ContactInfo(telegram_username="johndoe")
        
        assert contact.telegram_username == "johndoe"
        assert contact.telegram_user_id is None
        assert contact.phone_number is None
    
    def test_username_without_at_symbol(self):
        """Test that @ is automatically removed from username."""
        contact = ContactInfo(telegram_username="@johndoe")
        
        assert contact.telegram_username == "johndoe"
    
    def test_phone_normalization(self):
        """Test phone number normalization."""
        test_cases = [
            ("89991234567", "+79991234567"),
            ("+79991234567", "+79991234567"),
            ("8 999 123 45 67", "+79991234567"),
            ("8(999)123-45-67", "+79991234567"),
        ]
        
        for input_phone, expected in test_cases:
            contact = ContactInfo(phone_number=input_phone)
            assert contact.phone_number == expected
    
    def test_requires_at_least_one_contact(self):
        """Test that at least one contact method is required."""
        with pytest.raises(ValidationError) as exc_info:
            ContactInfo()
        
        assert "At least one contact method must be provided" in str(exc_info.value)
    
    def test_multiple_contacts(self):
        """Test creating contact with multiple fields."""
        contact = ContactInfo(
            telegram_username="johndoe",
            telegram_user_id=123456789,
            phone_number="+79991234567",
            other_contacts="email@example.com",
        )
        
        assert contact.telegram_username == "johndoe"
        assert contact.telegram_user_id == 123456789
        assert contact.phone_number == "+79991234567"
        assert contact.other_contacts == "email@example.com"


class TestMediaInfo:
    """Test MediaInfo Pydantic model."""
    
    def test_default_values(self):
        """Test default values."""
        media = MediaInfo()
        
        assert media.has_photo is False
        assert media.has_document is False
        assert media.photo_count == 0
        assert media.media_group_id is None
    
    def test_with_photo(self):
        """Test media with photo."""
        media = MediaInfo(has_photo=True, photo_count=3)
        
        assert media.has_photo is True
        assert media.photo_count == 3
    
    def test_media_group(self):
        """Test media group (album)."""
        media = MediaInfo(
            has_photo=True,
            photo_count=5,
            media_group_id=123456789,
        )
        
        assert media.has_photo is True
        assert media.photo_count == 5
        assert media.media_group_id == 123456789


class TestMessageData:
    """Test MessageData Pydantic model."""
    
    def test_valid_message_data(self):
        """Test creating valid message data."""
        data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам BMW 3 серии 2.5 Автомат 2008 года",
            date=datetime.now(),
        )
        
        assert data.message_id == 12345
        assert data.channel_id == "100123456789"
        assert len(data.text) > 0
    
    def test_text_too_short(self):
        """Test that short text is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            MessageData(
                message_id=12345,
                channel_id="100123456789",
                text="Short",  # Less than 10 chars
                date=datetime.now(),
            )
        
        assert "Message text too short" in str(exc_info.value)
    
    def test_text_whitespace_normalization(self):
        """Test that excessive whitespace is removed."""
        data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам   BMW    3 серии",  # Multiple spaces
            date=datetime.now(),
        )
        
        assert "  " not in data.text  # No double spaces
    
    def test_with_contacts(self):
        """Test message data with contacts."""
        contact = ContactInfo(telegram_username="seller")
        
        data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам BMW 3 серии",
            contacts=contact,
            date=datetime.now(),
        )
        
        assert data.contacts is not None
        assert data.contacts.telegram_username == "seller"
    
    def test_serialization(self):
        """Test model serialization."""
        data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам BMW 3 серии",
            date=datetime.now(),
        )
        
        # Test dict serialization
        dict_data = data.model_dump()
        assert isinstance(dict_data, dict)
        assert dict_data['message_id'] == 12345
        
        # Test JSON serialization
        json_data = data.model_dump_json()
        assert isinstance(json_data, str)
        assert '"message_id":12345' in json_data


class TestMessageProcessor:
    """Test MessageProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create MessageProcessor instance."""
        return MessageProcessor()
    
    @pytest.fixture
    def mock_message(self):
        """Create mock Telethon Message."""
        message = MagicMock()
        message.id = 12345
        message.message = "Продам BMW 3 серии 2.5 Автомат 2008. Контакт @seller, +79991234567"
        message.raw_text = message.message
        message.date = datetime.now()
        message.entities = []
        message.media = None
        message.grouped_id = None
        message.peer_id = MagicMock()
        message.peer_id.channel_id = 100123456789
        return message
    
    @pytest.fixture
    def mock_channel(self):
        """Create mock Channel."""
        channel = MagicMock()
        channel.id = 1
        channel.channel_id = "100123456789"
        channel.channel_username = "@testchannel"
        channel.channel_title = "Test Channel"
        channel.keywords = ["продам", "bmw"]
        channel.total_posts = 0
        return channel
    
    def test_check_keywords_match(self, processor):
        """Test keyword matching."""
        text = "Продам BMW 3 серии"
        keywords = ["продам", "bmw"]
        
        assert processor._check_keywords(text, keywords) is True
    
    def test_check_keywords_no_match(self, processor):
        """Test keyword non-matching."""
        text = "Куплю Mercedes"
        keywords = ["продам", "bmw"]
        
        assert processor._check_keywords(text, keywords) is False
    
    def test_check_keywords_case_insensitive(self, processor):
        """Test case-insensitive keyword matching."""
        text = "ПРОДАМ BMW"
        keywords = ["продам"]
        
        assert processor._check_keywords(text, keywords) is True
    
    def test_check_keywords_none(self, processor):
        """Test that None keywords means no filtering."""
        text = "Any text"
        keywords = None
        
        assert processor._check_keywords(text, keywords) is True
    
    def test_extract_username_from_text(self, processor):
        """Test extracting username from text."""
        text = "Контакт @johndoe для связи"
        matches = processor.USERNAME_PATTERN.findall(text)
        
        assert len(matches) > 0
        assert matches[0] == "johndoe"
    
    def test_extract_phone_from_text(self, processor):
        """Test extracting phone from text."""
        text = "Звоните +7 999 123-45-67"
        matches = processor.PHONE_PATTERN.findall(text)
        
        assert len(matches) > 0
    
    def test_extract_multiple_contacts(self, processor):
        """Test extracting multiple contacts."""
        text = "Контакт @seller или @backup, звоните +79991234567"
        
        usernames = processor.USERNAME_PATTERN.findall(text)
        phones = processor.PHONE_PATTERN.findall(text)
        
        assert len(usernames) == 2
        assert "seller" in usernames
        assert "backup" in usernames
        assert len(phones) > 0
    
    @pytest.mark.asyncio
    async def test_extract_message_data(self, processor, mock_message, mock_channel):
        """Test extracting data from message."""
        message_data = await processor._extract_message_data(mock_message, mock_channel)
        
        assert message_data is not None
        assert message_data.message_id == 12345
        assert message_data.channel_id == "100123456789"
        assert len(message_data.text) > 0
        assert message_data.date is not None
    
    @pytest.mark.asyncio
    async def test_is_duplicate_true(self, processor, mock_channel):
        """Test duplicate detection (found)."""
        message_data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам BMW 3 серии",
            date=datetime.now(),
        )
        
        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # Found
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        is_dup = await processor._is_duplicate(message_data, mock_channel, mock_session)
        
        assert is_dup is True
    
    @pytest.mark.asyncio
    async def test_is_duplicate_false(self, processor, mock_channel):
        """Test duplicate detection (not found)."""
        message_data = MessageData(
            message_id=12345,
            channel_id="100123456789",
            text="Продам BMW 3 серии",
            date=datetime.now(),
        )
        
        # Mock session
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not found
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        is_dup = await processor._is_duplicate(message_data, mock_channel, mock_session)
        
        assert is_dup is False
    
    @pytest.mark.asyncio
    async def test_extract_media_info_no_media(self, processor, mock_message):
        """Test extracting media info when no media."""
        mock_message.media = None
        
        media_info = processor._extract_media_info(mock_message)
        
        assert media_info.has_photo is False
        assert media_info.has_document is False
        assert media_info.photo_count == 0
    
    @pytest.mark.asyncio
    async def test_process_message_skipped_no_keywords(
        self, processor, mock_message, mock_channel
    ):
        """Test that message is skipped if doesn't match keywords."""
        mock_message.message = "Куплю Mercedes"  # Doesn't match keywords
        
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Not a duplicate
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        result = await processor.process_message(
            mock_message, mock_channel, mock_session
        )
        
        assert result is None  # Should be skipped


class TestContactExtraction:
    """Test contact extraction patterns."""
    
    def test_phone_patterns(self):
        """Test various phone number formats."""
        processor = MessageProcessor()
        
        test_cases = [
            "+7 999 123-45-67",
            "8 (999) 123-45-67",
            "89991234567",
            "+1-555-123-4567",
            "8-800-555-35-35",
        ]
        
        for phone in test_cases:
            matches = processor.PHONE_PATTERN.findall(phone)
            assert len(matches) > 0, f"Failed to match: {phone}"
    
    def test_username_patterns(self):
        """Test various username formats."""
        processor = MessageProcessor()
        
        test_cases = [
            ("@johndoe", "johndoe"),
            ("контакт @seller для", "seller"),
            ("@user_name_123", "user_name_123"),
        ]
        
        for text, expected in test_cases:
            matches = processor.USERNAME_PATTERN.findall(text)
            assert len(matches) > 0
            assert expected in matches


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


