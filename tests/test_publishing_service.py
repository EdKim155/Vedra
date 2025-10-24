"""
Tests for Publishing Service.

Tests post formatting and publishing functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cars_bot.database.enums import AutotekaStatus, TransmissionType
from cars_bot.database.models.car_data import CarData
from cars_bot.database.models.post import Post
from cars_bot.publishing.service import PublishingService


class TestPublishingService:
    """Test PublishingService class."""
    
    @pytest.fixture
    def mock_bot(self):
        """Create mock Bot instance."""
        bot = MagicMock()
        bot.send_message = AsyncMock()
        bot.send_photo = AsyncMock()
        bot.send_media_group = AsyncMock()
        bot.edit_message_text = AsyncMock()
        bot.delete_message = AsyncMock()
        return bot
    
    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session
    
    @pytest.fixture
    def publishing_service(self, mock_bot, mock_session):
        """Create PublishingService instance."""
        return PublishingService(
            bot=mock_bot,
            channel_id="-1001234567890",
            session=mock_session
        )
    
    @pytest.fixture
    def sample_car_data(self):
        """Create sample CarData instance."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="BMW",
            model="3 серии",
            engine_volume="2.5",
            transmission=TransmissionType.AUTOMATIC,
            year=2008,
            owners_count=2,
            mileage=150000,
            autoteka_status=AutotekaStatus.GREEN,
            equipment="Кожаный салон, подогрев сидений, парктроник",
            price=850000,
            market_price=900000,
            price_justification="Цена ниже рынка на 50 000₽"
        )
        return car_data
    
    def test_format_header(self, publishing_service, sample_car_data):
        """Test header formatting."""
        header = publishing_service._format_header(sample_car_data)
        
        assert "🚗" in header
        assert "BMW" in header
        assert "3 серии" in header
        assert "<b>" in header
    
    def test_format_specs(self, publishing_service, sample_car_data):
        """Test specs line formatting."""
        specs = publishing_service._format_specs(sample_car_data)
        
        assert "📋" in specs
        assert "2.5л" in specs
        assert "Автомат" in specs
        assert "2008" in specs
        assert "•" in specs
    
    def test_format_history(self, publishing_service, sample_car_data):
        """Test history block formatting."""
        history = publishing_service._format_history(sample_car_data)
        
        assert "📊" in history
        assert "История автомобиля" in history
        assert "2 владельца" in history
        assert "150 000 км" in history
        assert "✅ чистая" in history
    
    def test_format_history_with_no_data(self, publishing_service):
        """Test history formatting with missing data."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="BMW",
            model="3 серии"
        )
        
        history = publishing_service._format_history(car_data)
        
        assert "📊" in history
        assert "Данные уточняются" in history
    
    def test_format_equipment(self, publishing_service, sample_car_data):
        """Test equipment block formatting."""
        equipment = publishing_service._format_equipment(
            sample_car_data,
            processed_text=None
        )
        
        assert "⚙️" in equipment
        assert "Комплектация" in equipment
        assert "Кожаный салон" in equipment
    
    def test_format_equipment_with_processed_text(self, publishing_service, sample_car_data):
        """Test equipment formatting with processed text."""
        processed_text = "Отличная комплектация с кожей и подогревом"
        
        equipment = publishing_service._format_equipment(
            sample_car_data,
            processed_text=processed_text
        )
        
        assert processed_text in equipment
    
    def test_format_price(self, publishing_service, sample_car_data):
        """Test price block formatting."""
        price = publishing_service._format_price(sample_car_data)
        
        assert "💰" in price
        assert "850 000₽" in price
        assert "Рыночная цена" in price
        assert "900 000₽" in price
        assert "выгода" in price
    
    def test_format_price_without_market_comparison(self, publishing_service):
        """Test price formatting without market price."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="BMW",
            price=850000
        )
        
        price = publishing_service._format_price(car_data)
        
        assert "💰" in price
        assert "850 000₽" in price
        assert "Рыночная цена" not in price
    
    def test_format_post_complete(self, publishing_service, sample_car_data):
        """Test complete post formatting."""
        post_text = publishing_service.format_post(
            car_data=sample_car_data,
            processed_text="Отличный автомобиль в хорошем состоянии"
        )
        
        # Check all sections are present
        assert "🚗" in post_text
        assert "BMW 3 серии" in post_text
        assert "📋" in post_text
        assert "2.5л" in post_text
        assert "📊" in post_text
        assert "История автомобиля" in post_text
        assert "⚙️" in post_text
        assert "Комплектация" in post_text
        assert "💰" in post_text
        assert "850 000₽" in post_text
    
    def test_get_owners_text_single(self, publishing_service):
        """Test owners text for single owner."""
        text = publishing_service._get_owners_text(1)
        assert text == "1 владелец"
    
    def test_get_owners_text_multiple(self, publishing_service):
        """Test owners text for multiple owners."""
        assert publishing_service._get_owners_text(2) == "2 владельца"
        assert publishing_service._get_owners_text(3) == "3 владельца"
        assert publishing_service._get_owners_text(5) == "5 владельцев"
    
    def test_get_autoteka_status_text(self, publishing_service):
        """Test autoteka status text."""
        assert "✅" in publishing_service._get_autoteka_status_text(AutotekaStatus.GREEN)
        assert "⚠️" in publishing_service._get_autoteka_status_text(AutotekaStatus.HAS_ACCIDENTS)
        assert "❓" in publishing_service._get_autoteka_status_text(AutotekaStatus.UNKNOWN)
    
    @pytest.mark.asyncio
    async def test_publish_text_only(self, publishing_service, mock_bot):
        """Test publishing text-only post."""
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_bot.send_message.return_value = mock_message
        
        keyboard = MagicMock()
        message_id = await publishing_service._publish_text_only(
            "Test text",
            keyboard
        )
        
        assert message_id == 12345
        mock_bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_with_single_media(self, publishing_service, mock_bot):
        """Test publishing with single photo."""
        mock_message = MagicMock()
        mock_message.message_id = 12345
        mock_bot.send_photo.return_value = mock_message
        
        keyboard = MagicMock()
        media_urls = ["https://example.com/photo1.jpg"]
        
        message_id = await publishing_service._publish_with_media(
            "Test caption",
            media_urls,
            keyboard
        )
        
        assert message_id == 12345
        mock_bot.send_photo.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_publish_with_multiple_media(self, publishing_service, mock_bot):
        """Test publishing with multiple photos."""
        mock_messages = [MagicMock(), MagicMock()]
        mock_messages[0].message_id = 12345
        mock_messages[1].message_id = 12346
        mock_bot.send_media_group.return_value = mock_messages
        
        mock_button_message = MagicMock()
        mock_button_message.message_id = 12347
        mock_bot.send_message.return_value = mock_button_message
        
        keyboard = MagicMock()
        media_urls = [
            "https://example.com/photo1.jpg",
            "https://example.com/photo2.jpg"
        ]
        
        message_id = await publishing_service._publish_with_media(
            "Test caption",
            media_urls,
            keyboard
        )
        
        assert message_id == 12345
        mock_bot.send_media_group.assert_called_once()
        mock_bot.send_message.assert_called_once()
    
    def test_format_post_minimal_data(self, publishing_service):
        """Test formatting with minimal car data."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="Toyota",
            model="Camry"
        )
        
        post_text = publishing_service.format_post(car_data)
        
        assert "Toyota Camry" in post_text
        assert "🚗" in post_text
        # Should handle missing data gracefully
        assert "уточняется" in post_text or "Данные" in post_text


class TestPostFormattingEdgeCases:
    """Test edge cases in post formatting."""
    
    @pytest.fixture
    def publishing_service(self):
        """Create PublishingService with mocks."""
        return PublishingService(
            bot=MagicMock(),
            channel_id="-1001234567890",
            session=MagicMock()
        )
    
    def test_format_post_with_empty_strings(self, publishing_service):
        """Test formatting with empty string values."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="",
            model="",
            equipment=""
        )
        
        post_text = publishing_service.format_post(car_data)
        
        # Should not crash and provide defaults
        assert "🚗" in post_text
        assert len(post_text) > 0
    
    def test_format_price_very_large(self, publishing_service):
        """Test formatting with very large price."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="Porsche",
            price=15000000
        )
        
        price = publishing_service._format_price(car_data)
        
        assert "15 000 000₽" in price
    
    def test_format_mileage_zero(self, publishing_service):
        """Test formatting with zero mileage."""
        car_data = CarData(
            id=1,
            post_id=1,
            brand="BMW",
            mileage=0
        )
        
        history = publishing_service._format_history(car_data)
        
        assert "0 км" in history



